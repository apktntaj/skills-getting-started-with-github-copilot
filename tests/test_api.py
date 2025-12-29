"""
Test suite for Mergington High School API
"""
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original participants
    original_participants = {
        activity_name: details["participants"].copy()
        for activity_name, details in activities.items()
    }
    
    yield
    
    # Restore original participants after each test
    for activity_name, participants in original_participants.items():
        activities[activity_name]["participants"] = participants


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root path redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        
        # Check that expected activities exist
        assert "Soccer Team" in data
        assert "Basketball Club" in data
        assert "Programming Class" in data
    
    def test_activities_have_required_fields(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, details in data.items():
            assert "description" in details
            assert "schedule" in details
            assert "max_participants" in details
            assert "participants" in details
            assert isinstance(details["participants"], list)
            assert isinstance(details["max_participants"], int)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_new_participant_success(self, client):
        """Test successful signup of a new participant"""
        response = client.post(
            "/activities/Soccer Team/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
        assert "Soccer Team" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "test@mergington.edu" in activities_data["Soccer Team"]["participants"]
    
    def test_signup_duplicate_participant_fails(self, client):
        """Test that signing up the same participant twice fails"""
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(
            f"/activities/Soccer Team/signup?email={email}"
        )
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(
            f"/activities/Soccer Team/signup?email={email}"
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"].lower()
    
    def test_signup_nonexistent_activity_fails(self, client):
        """Test that signing up for a nonexistent activity fails"""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_signup_with_special_characters_in_activity_name(self, client):
        """Test signup with URL encoding in activity name"""
        response = client.post(
            "/activities/Programming%20Class/signup?email=coder@mergington.edu"
        )
        assert response.status_code == 200


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_existing_participant_success(self, client):
        """Test successful unregistration of an existing participant"""
        email = "unregister@mergington.edu"
        
        # First signup
        client.post(f"/activities/Soccer Team/signup?email={email}")
        
        # Then unregister
        response = client.delete(
            f"/activities/Soccer Team/unregister?email={email}"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert "Unregistered" in data["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data["Soccer Team"]["participants"]
    
    def test_unregister_nonexistent_participant_fails(self, client):
        """Test that unregistering a non-existent participant fails"""
        response = client.delete(
            "/activities/Soccer Team/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_unregister_from_nonexistent_activity_fails(self, client):
        """Test that unregistering from a nonexistent activity fails"""
        response = client.delete(
            "/activities/Nonexistent Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_unregister_existing_default_participant(self, client):
        """Test unregistering a participant that was already in the activity"""
        # Alex is already in Soccer Team by default
        response = client.delete(
            "/activities/Soccer Team/unregister?email=alex@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify removal
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "alex@mergington.edu" not in activities_data["Soccer Team"]["participants"]


class TestEndToEndWorkflow:
    """End-to-end integration tests"""
    
    def test_complete_signup_and_unregister_workflow(self, client):
        """Test complete workflow of signup and unregister"""
        email = "workflow@mergington.edu"
        activity = "Drama Club"
        
        # Get initial state
        initial_response = client.get("/activities")
        initial_data = initial_response.json()
        initial_count = len(initial_data[activity]["participants"])
        
        # Signup
        signup_response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Verify participant added
        after_signup_response = client.get("/activities")
        after_signup_data = after_signup_response.json()
        assert len(after_signup_data[activity]["participants"]) == initial_count + 1
        assert email in after_signup_data[activity]["participants"]
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        
        # Verify participant removed
        after_unregister_response = client.get("/activities")
        after_unregister_data = after_unregister_response.json()
        assert len(after_unregister_data[activity]["participants"]) == initial_count
        assert email not in after_unregister_data[activity]["participants"]
    
    def test_multiple_participants_signup(self, client):
        """Test multiple participants can sign up for the same activity"""
        activity = "Chess Club"
        emails = [
            "player1@mergington.edu",
            "player2@mergington.edu",
            "player3@mergington.edu"
        ]
        
        for email in emails:
            response = client.post(
                f"/activities/{activity}/signup?email={email}"
            )
            assert response.status_code == 200
        
        # Verify all participants added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        
        for email in emails:
            assert email in activities_data[activity]["participants"]
