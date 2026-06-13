"""add tsvector trigger for course search

Revision ID: c6656b3462dc
Revises: 90eafcbbec13
Create Date: 2026-06-14
"""
from alembic import op

revision = "c6656b3462dc"
down_revision = "90eafcbbec13"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_courses_search_vector
        ON courses USING GIN(search_vector)
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION update_course_search_vector()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(NEW.description, '')), 'B');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS courses_search_vector_update ON courses
    """)

    op.execute("""
        CREATE TRIGGER courses_search_vector_update
        BEFORE INSERT OR UPDATE ON courses
        FOR EACH ROW EXECUTE FUNCTION update_course_search_vector()
    """)

    op.execute("""
        UPDATE courses SET search_vector =
            setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(description, '')), 'B')
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS courses_search_vector_update ON courses")
    op.execute("DROP FUNCTION IF EXISTS update_course_search_vector")
    op.execute("DROP INDEX IF EXISTS ix_courses_search_vector")