import pytest


async def create_course_helper(client, **kwargs):
    data = {
        "title": "Test Course",
        "description": "A detailed description of this course",
        "price": 0.0,
        "difficulty": "beginner",
        **kwargs,
    }
    return await client.post("/api/v1/courses", json=data)


async def add_lesson_helper(client, course_id: str) -> None:
    """Add section + lesson so course can be published."""
    section = await client.post(
        f"/api/v1/courses/{course_id}/sections",
        json={"title": "Section 1"},
    )
    section_id = section.json()["id"]
    await client.post(
        f"/api/v1/sections/{section_id}/lessons",
        json={"title": "Lesson 1", "lesson_type": "article"},
    )


class TestCreateCourse:
    async def test_instructor_can_create(self, instructor_client):
        response = await create_course_helper(instructor_client)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "draft"
        assert data["title"] == "Test Course"

    async def test_student_cannot_create(self, student_client):
        response = await create_course_helper(student_client)
        assert response.status_code == 403

    async def test_missing_title_returns_422(self, instructor_client):
        response = await instructor_client.post(
            "/api/v1/courses",
            json={"description": "No title here"},
        )
        assert response.status_code == 422


class TestGetCourse:
    async def test_instructor_sees_draft(self, instructor_client):
        create = await create_course_helper(instructor_client, title="Draft Course")
        course_id = create.json()["id"]

        response = await instructor_client.get(f"/api/v1/courses/{course_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "draft"

    async def test_student_cannot_see_draft(self, instructor_client, student_token, client):
        create = await create_course_helper(instructor_client, title="Hidden Draft")
        course_id = create.json()["id"]

        response = await client.get(
            f"/api/v1/courses/{course_id}",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert response.status_code == 404


class TestUpdateCourse:
    async def test_owner_can_update(self, instructor_client):
        create = await create_course_helper(instructor_client, title="Old Title")
        course_id = create.json()["id"]

        response = await instructor_client.patch(
            f"/api/v1/courses/{course_id}",
            json={"title": "New Title"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "New Title"


class TestPublishCourse:
    async def test_publish_success(self, instructor_client):
        create = await create_course_helper(instructor_client, title="To Publish")
        course_id = create.json()["id"]
        await add_lesson_helper(instructor_client, course_id)

        response = await instructor_client.post(f"/api/v1/courses/{course_id}/publish")
        assert response.status_code == 200
        assert response.json()["status"] == "published"

    async def test_publish_without_lessons_fails(self, instructor_client):
        create = await create_course_helper(instructor_client, title="Empty Course")
        course_id = create.json()["id"]

        response = await instructor_client.post(f"/api/v1/courses/{course_id}/publish")
        assert response.status_code == 400

    async def test_unpublish_success(self, instructor_client):
        create = await create_course_helper(instructor_client, title="To Unpublish")
        course_id = create.json()["id"]
        await add_lesson_helper(instructor_client, course_id)

        await instructor_client.post(f"/api/v1/courses/{course_id}/publish")
        response = await instructor_client.post(f"/api/v1/courses/{course_id}/unpublish")
        assert response.status_code == 200
        assert response.json()["status"] == "draft"


class TestDeleteCourse:
    async def test_soft_delete(self, instructor_client):
        create = await create_course_helper(instructor_client, title="To Delete")
        course_id = create.json()["id"]

        response = await instructor_client.delete(f"/api/v1/courses/{course_id}")
        assert response.status_code == 204

        get = await instructor_client.get(f"/api/v1/courses/{course_id}")
        assert get.status_code == 404


class TestListCourses:
    async def test_returns_only_published(self, instructor_client, student_token, client):
        create = await create_course_helper(instructor_client, title="Published Course")
        course_id = create.json()["id"]
        await add_lesson_helper(instructor_client, course_id)
        await instructor_client.post(f"/api/v1/courses/{course_id}/publish")

        response = await client.get(
            "/api/v1/courses",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert all(c["status"] == "published" for c in data["items"])

    async def test_categories_endpoint(self, client, student_token):
        response = await client.get(
            "/api/v1/courses/categories/all",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)