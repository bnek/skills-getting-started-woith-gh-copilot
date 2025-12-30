"""
Tests for the High School Management System API
"""
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original data
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original data after test
    for name in activities:
        activities[name]["participants"] = original_activities[name]["participants"].copy()


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for getting activities"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that get activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        assert "Soccer Team" in data
        assert "Basketball Club" in data
    
    def test_get_activities_structure(self, client):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)


class TestSignupForActivity:
    """Tests for signing up for activities"""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        response = client.post("/activities/Soccer%20Team/signup?email=test@mergington.edu")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
        assert "Soccer Team" in data["message"]
        
        # Verify the participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "test@mergington.edu" in activities_data["Soccer Team"]["participants"]
    
    def test_signup_duplicate_email(self, client):
        """Test that duplicate signups are rejected"""
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(f"/activities/Soccer%20Team/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/Soccer%20Team/signup?email={email}")
        assert response2.status_code == 400
        data = response2.json()
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_nonexistent_activity(self, client):
        """Test signup for non-existent activity"""
        response = client.post("/activities/NonExistent/signup?email=test@mergington.edu")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_signup_with_special_characters_in_email(self, client):
        """Test signup with special characters in email"""
        from urllib.parse import quote
        email = "test+special@mergington.edu"
        response = client.post(f"/activities/Soccer%20Team/signup?email={quote(email)}")
        assert response.status_code == 200
        
        # Verify the participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data["Soccer Team"]["participants"]


class TestUnregisterFromActivity:
    """Tests for unregistering from activities"""
    
    def test_unregister_success(self, client):
        """Test successful unregister from an activity"""
        # First signup
        email = "unregister@mergington.edu"
        signup_response = client.post(f"/activities/Soccer%20Team/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Then unregister
        response = client.delete(f"/activities/Soccer%20Team/unregister?email={email}")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert "Soccer Team" in data["message"]
        
        # Verify the participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data["Soccer Team"]["participants"]
    
    def test_unregister_not_registered(self, client):
        """Test unregistering a participant not registered for activity"""
        email = "notregistered@mergington.edu"
        response = client.delete(f"/activities/Soccer%20Team/unregister?email={email}")
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"].lower()
    
    def test_unregister_nonexistent_activity(self, client):
        """Test unregister from non-existent activity"""
        response = client.delete("/activities/NonExistent/unregister?email=test@mergington.edu")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_unregister_existing_participant(self, client):
        """Test unregistering an existing participant"""
        # Soccer Team has alex@mergington.edu and sarah@mergington.edu
        email = "alex@mergington.edu"
        
        # Verify they are registered
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data["Soccer Team"]["participants"]
        
        # Unregister
        response = client.delete(f"/activities/Soccer%20Team/unregister?email={email}")
        assert response.status_code == 200
        
        # Verify they were removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data["Soccer Team"]["participants"]


class TestFullWorkflow:
    """Integration tests for complete workflows"""
    
    def test_signup_and_unregister_workflow(self, client):
        """Test complete workflow of signup and unregister"""
        email = "workflow@mergington.edu"
        activity = "Programming Class"
        
        # Get initial participant count
        initial_response = client.get("/activities")
        initial_data = initial_response.json()
        initial_count = len(initial_data[activity]["participants"])
        
        # Signup
        signup_response = client.post(f"/activities/{activity.replace(' ', '%20')}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Verify count increased
        after_signup_response = client.get("/activities")
        after_signup_data = after_signup_response.json()
        assert len(after_signup_data[activity]["participants"]) == initial_count + 1
        assert email in after_signup_data[activity]["participants"]
        
        # Unregister
        unregister_response = client.delete(f"/activities/{activity.replace(' ', '%20')}/unregister?email={email}")
        assert unregister_response.status_code == 200
        
        # Verify count back to original
        final_response = client.get("/activities")
        final_data = final_response.json()
        assert len(final_data[activity]["participants"]) == initial_count
        assert email not in final_data[activity]["participants"]
    
    def test_multiple_signups_different_activities(self, client):
        """Test a student signing up for multiple activities"""
        email = "multi@mergington.edu"
        
        # Signup for multiple activities
        activities_to_join = ["Soccer Team", "Drama Club", "Chess Club"]
        
        for activity in activities_to_join:
            response = client.post(f"/activities/{activity.replace(' ', '%20')}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify student is in all activities
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        
        for activity in activities_to_join:
            assert email in activities_data[activity]["participants"]
