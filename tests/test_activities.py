"""
Tests for the activities API endpoints
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add the src directory to the path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities before each test"""
    # Store original state
    original_participants = {
        activity: details["participants"].copy()
        for activity, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for activity, details in activities.items():
        details["participants"] = original_participants[activity]


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        assert "Chess Club" in data
        assert "Programming Class" in data
    
    def test_get_activities_includes_required_fields(self, client, reset_activities):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)
    
    def test_chess_club_has_existing_participants(self, client, reset_activities):
        """Test that Chess Club has the expected participants"""
        response = client.get("/activities")
        data = response.json()
        chess_club = data["Chess Club"]
        
        assert len(chess_club["participants"]) == 2
        assert "michael@mergington.edu" in chess_club["participants"]
        assert "daniel@mergington.edu" in chess_club["participants"]


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_successful(self, client, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Basketball%20Team/signup?email=newstudent@mergington.edu"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Basketball Team" in data["message"]
    
    def test_signup_adds_participant_to_activity(self, client, reset_activities):
        """Test that signup actually adds the participant"""
        email = "test@mergington.edu"
        client.post(f"/activities/Art%20Club/signup?email={email}")
        
        response = client.get("/activities")
        data = response.json()
        assert email in data["Art Club"]["participants"]
    
    def test_signup_to_nonexistent_activity(self, client, reset_activities):
        """Test signup to an activity that doesn't exist"""
        response = client.post(
            "/activities/Nonexistent%20Club/signup?email=test@mergington.edu"
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_signup_duplicate_student(self, client, reset_activities):
        """Test that a student can't sign up twice for the same activity"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=michael@mergington.edu"
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Student is already signed up"
    
    def test_signup_multiple_students_same_activity(self, client, reset_activities):
        """Test that multiple different students can sign up"""
        students = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        for student in students:
            response = client.post(f"/activities/Drama%20Club/signup?email={student}")
            assert response.status_code == 200
        
        response = client.get("/activities")
        data = response.json()
        for student in students:
            assert student in data["Drama Club"]["participants"]
    
    def test_signup_same_student_different_activities(self, client, reset_activities):
        """Test that a student can sign up for multiple different activities"""
        email = "versatile@mergington.edu"
        activities_to_join = ["Chess Club", "Drama Club", "Art Club"]
        
        for activity in activities_to_join:
            response = client.post(
                f"/activities/{activity.replace(' ', '%20')}/signup?email={email}"
            )
            assert response.status_code == 200
        
        response = client.get("/activities")
        data = response.json()
        for activity in activities_to_join:
            assert email in data[activity]["participants"]


class TestRemoveParticipant:
    """Tests for DELETE /activities/{activity_name}/participants/{email} endpoint"""
    
    def test_remove_participant_successful(self, client, reset_activities):
        """Test successful removal of a participant"""
        response = client.delete(
            "/activities/Chess%20Club/participants/michael@mergington.edu"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "michael@mergington.edu" in data["message"]
    
    def test_remove_participant_removes_from_list(self, client, reset_activities):
        """Test that removal actually removes the participant"""
        client.delete(
            "/activities/Chess%20Club/participants/michael@mergington.edu"
        )
        
        response = client.get("/activities")
        data = response.json()
        assert "michael@mergington.edu" not in data["Chess Club"]["participants"]
        assert "daniel@mergington.edu" in data["Chess Club"]["participants"]
    
    def test_remove_participant_from_nonexistent_activity(self, client, reset_activities):
        """Test removing from an activity that doesn't exist"""
        response = client.delete(
            "/activities/Nonexistent%20Club/participants/test@mergington.edu"
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_remove_nonexistent_participant(self, client, reset_activities):
        """Test removing a participant that's not in the activity"""
        response = client.delete(
            "/activities/Chess%20Club/participants/nonexistent@mergington.edu"
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Participant not found in activity"
    
    def test_remove_all_participants(self, client, reset_activities):
        """Test removing all participants from an activity"""
        participants = ["michael@mergington.edu", "daniel@mergington.edu"]
        
        for participant in participants:
            response = client.delete(
                f"/activities/Chess%20Club/participants/{participant}"
            )
            assert response.status_code == 200
        
        response = client.get("/activities")
        data = response.json()
        assert len(data["Chess Club"]["participants"]) == 0
    
    def test_remove_and_readd_participant(self, client, reset_activities):
        """Test removing and then re-adding a participant"""
        email = "test@mergington.edu"
        activity = "Basketball%20Team"
        
        # Sign up
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
        
        # Remove
        response = client.delete(f"/activities/{activity}/participants/{email}")
        assert response.status_code == 200
        
        # Verify removed
        response = client.get("/activities")
        data = response.json()
        assert email not in data["Basketball Team"]["participants"]
        
        # Sign up again
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
        
        # Verify re-added
        response = client.get("/activities")
        data = response.json()
        assert email in data["Basketball Team"]["participants"]


class TestRootEndpoint:
    """Tests for GET / endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root endpoint redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"
