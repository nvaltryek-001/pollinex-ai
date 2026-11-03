"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-02
"""
import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table("roles",
                    sa.Column("id", sa.Integer, primary_key=True),
                    sa.Column("name", sa.String(32), nullable=False, unique=True),
                    sa.Column("description", sa.String(255), nullable=False))
    op.create_table("users",
                    sa.Column("id", sa.Integer, primary_key=True),
                    sa.Column("email", sa.String(255), nullable=False),
                    sa.Column("full_name", sa.String(120), nullable=False),
                    sa.Column("password_hash", sa.String(255), nullable=False),
                    sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id"), nullable=False),
                    sa.Column("is_active", sa.Boolean, nullable=False),
                    sa.Column("token_version", sa.Integer, nullable=False),
                    sa.Column("created_at", TS, nullable=False))
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table("species",
                    sa.Column("id", sa.String(40), primary_key=True),
                    sa.Column("common_name", sa.String(120), nullable=False),
                    sa.Column("scientific_name", sa.String(160), nullable=False),
                    sa.Column("primary_mechanism", sa.String(40), nullable=False),
                    sa.Column("knowledge", sa.JSON, nullable=False),
                    sa.Column("reference_image_count", sa.Integer, nullable=False))
    op.create_table("field_locations",
                    sa.Column("id", sa.Integer, primary_key=True),
                    sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
                    sa.Column("name", sa.String(120), nullable=False),
                    sa.Column("latitude", sa.Float), sa.Column("longitude", sa.Float), sa.Column("area_m2", sa.Float),
                    sa.Column("notes", sa.Text, nullable=False),
                    sa.Column("created_at", TS, nullable=False))
    op.create_index("ix_field_locations_owner_id", "field_locations", ["owner_id"])
    op.create_table("plants",
                    sa.Column("id", sa.Integer, primary_key=True),
                    sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
                    sa.Column("field_id", sa.Integer, sa.ForeignKey("field_locations.id", ondelete="SET NULL")),
                    sa.Column("species_id", sa.String(40), sa.ForeignKey("species.id")),
                    sa.Column("label", sa.String(120), nullable=False),
                    sa.Column("cultivar", sa.String(120), nullable=False),
                    sa.Column("planted_on", sa.String(10)),
                    sa.Column("notes", sa.Text, nullable=False),
                    sa.Column("created_at", TS, nullable=False))
    op.create_index("ix_plants_owner_id", "plants", ["owner_id"])
    op.create_index("ix_plants_field_id", "plants", ["field_id"])
    op.create_table("uploaded_images",
                    sa.Column("id", sa.Integer, primary_key=True),
                    sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
                    sa.Column("storage_path", sa.String(400), nullable=False),
                    sa.Column("original_name", sa.String(255), nullable=False),
                    sa.Column("content_type", sa.String(40), nullable=False),
                    sa.Column("width", sa.Integer, nullable=False), sa.Column("height", sa.Integer, nullable=False),
                    sa.Column("size_bytes", sa.Integer, nullable=False),
                    sa.Column("sha256", sa.String(64), nullable=False),
                    sa.Column("created_at", TS, nullable=False))
    op.create_index("ix_uploaded_images_owner_id", "uploaded_images", ["owner_id"])
    op.create_index("ix_uploaded_images_sha256", "uploaded_images", ["sha256"])
    op.create_table("environment_records",
                    sa.Column("id", sa.Integer, primary_key=True),
                    sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
                    sa.Column("field_id", sa.Integer, sa.ForeignKey("field_locations.id", ondelete="SET NULL")),
                    sa.Column("observed_at", TS, nullable=False),
                    sa.Column("temperature_c", sa.Float), sa.Column("relative_humidity_pct", sa.Float),
                    sa.Column("rain_mm_h", sa.Float), sa.Column("wind_kmh", sa.Float),
                    sa.Column("observation", sa.Text, nullable=False),
                    sa.Column("source", sa.String(80), nullable=False),
                    sa.Column("source_detail", sa.JSON, nullable=False),
                    sa.Column("created_at", TS, nullable=False))
    op.create_index("ix_environment_records_owner_id", "environment_records", ["owner_id"])
    op.create_index("ix_environment_records_observed_at", "environment_records", ["observed_at"])
    op.create_table("model_versions",
                    sa.Column("id", sa.Integer, primary_key=True),
                    sa.Column("name", sa.String(80), nullable=False), sa.Column("version", sa.String(80), nullable=False),
                    sa.Column("task", sa.String(40), nullable=False), sa.Column("backend", sa.String(80), nullable=False),
                    sa.Column("is_active", sa.Boolean, nullable=False), sa.Column("details", sa.JSON, nullable=False),
                    sa.Column("registered_at", TS, nullable=False))
    op.create_index("ix_model_task_version", "model_versions", ["task", "version"], unique=True)
    op.create_table("scans",
                    sa.Column("id", sa.Integer, primary_key=True),
                    sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
                    sa.Column("image_id", sa.Integer, sa.ForeignKey("uploaded_images.id", ondelete="CASCADE"), nullable=False),
                    sa.Column("plant_id", sa.Integer, sa.ForeignKey("plants.id", ondelete="SET NULL")),
                    sa.Column("field_id", sa.Integer, sa.ForeignKey("field_locations.id", ondelete="SET NULL")),
                    sa.Column("environment_id", sa.Integer, sa.ForeignKey("environment_records.id", ondelete="SET NULL")),
                    sa.Column("model_version_id", sa.Integer, sa.ForeignKey("model_versions.id")),
                    sa.Column("source", sa.String(20), nullable=False), sa.Column("mode", sa.String(16), nullable=False),
                    sa.Column("species_hint", sa.String(40)), sa.Column("status", sa.String(16), nullable=False),
                    sa.Column("detection_method", sa.String(32), nullable=False),
                    sa.Column("flower_count", sa.Integer, nullable=False), sa.Column("latency_ms", sa.Float, nullable=False),
                    sa.Column("warnings", sa.JSON, nullable=False), sa.Column("summary", sa.JSON, nullable=False),
                    sa.Column("created_at", TS, nullable=False))
    op.create_index("ix_scans_owner_id", "scans", ["owner_id"])
    op.create_index("ix_scans_created_at", "scans", ["created_at"])
    op.create_table("flower_detections",
                    sa.Column("id", sa.Integer, primary_key=True),
                    sa.Column("scan_id", sa.Integer, sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False),
                    sa.Column("index", sa.Integer, nullable=False),
                    sa.Column("x1", sa.Float, nullable=False), sa.Column("y1", sa.Float, nullable=False),
                    sa.Column("x2", sa.Float, nullable=False), sa.Column("y2", sa.Float, nullable=False),
                    sa.Column("score", sa.Float, nullable=False), sa.Column("low_confidence", sa.Boolean, nullable=False),
                    sa.Column("method", sa.String(32), nullable=False),
                    sa.Column("species_id", sa.String(40), nullable=False),
                    sa.Column("species_confidence", sa.Float, nullable=False),
                    sa.Column("species_method", sa.String(40), nullable=False),
                    sa.Column("pose", sa.JSON, nullable=False), sa.Column("health", sa.JSON, nullable=False))
    op.create_index("ix_flower_detections_scan_id", "flower_detections", ["scan_id"])
    op.create_index("ix_flower_detections_species_id", "flower_detections", ["species_id"])
    for name, extra in (("structure_detections", [sa.Column("method", sa.String(32), nullable=False),
                                                  sa.Column("structure_detection_available", sa.Boolean, nullable=False),
                                                  sa.Column("yellow_cluster_visible", sa.Boolean, nullable=False)]),
                        ("maturity_predictions", [sa.Column("stage", sa.String(24), nullable=False),
                                                  sa.Column("score", sa.Float, nullable=False),
                                                  sa.Column("method", sa.String(32), nullable=False),
                                                  sa.Column("uncertain", sa.Boolean, nullable=False)]),
                        ("readiness_predictions", [sa.Column("category", sa.String(24), nullable=False),
                                                   sa.Column("confidence", sa.Float, nullable=False)])):
        op.create_table(name, sa.Column("id", sa.Integer, primary_key=True),
                        sa.Column("detection_id", sa.Integer, sa.ForeignKey("flower_detections.id", ondelete="CASCADE"),
                                  nullable=False, unique=True),
                        *extra, sa.Column("data", sa.JSON, nullable=False))
    op.create_index("ix_maturity_predictions_stage", "maturity_predictions", ["stage"])
    op.create_index("ix_readiness_predictions_category", "readiness_predictions", ["category"])
    op.create_table("pollination_records",
                    sa.Column("id", sa.Integer, primary_key=True),
                    sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
                    sa.Column("plant_id", sa.Integer, sa.ForeignKey("plants.id", ondelete="SET NULL")),
                    sa.Column("scan_id", sa.Integer, sa.ForeignKey("scans.id", ondelete="SET NULL")),
                    sa.Column("species_id", sa.String(40)), sa.Column("method", sa.String(40), nullable=False),
                    sa.Column("performed_at", TS, nullable=False), sa.Column("flowers_treated", sa.Integer, nullable=False),
                    sa.Column("outcome_observed", sa.String(40)), sa.Column("notes", sa.Text, nullable=False),
                    sa.Column("created_at", TS, nullable=False))
    op.create_index("ix_pollination_records_owner_id", "pollination_records", ["owner_id"])
    op.create_table("simulations",
                    sa.Column("id", sa.Integer, primary_key=True),
                    sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
                    sa.Column("scan_id", sa.Integer, sa.ForeignKey("scans.id", ondelete="SET NULL")),
                    sa.Column("species_id", sa.String(40), nullable=False), sa.Column("status", sa.String(16), nullable=False),
                    sa.Column("params", sa.JSON, nullable=False), sa.Column("result_summary", sa.JSON, nullable=False),
                    sa.Column("result_path", sa.String(400)), sa.Column("sim_version", sa.String(20), nullable=False),
                    sa.Column("created_at", TS, nullable=False), sa.Column("completed_at", TS))
    op.create_index("ix_simulations_owner_id", "simulations", ["owner_id"])
    op.create_index("ix_simulations_created_at", "simulations", ["created_at"])
    op.create_table("evaluation_runs",
                    sa.Column("id", sa.Integer, primary_key=True),
                    sa.Column("model_version_id", sa.Integer, sa.ForeignKey("model_versions.id")),
                    sa.Column("task", sa.String(40), nullable=False), sa.Column("dataset_id", sa.String(80), nullable=False),
                    sa.Column("split", sa.String(20), nullable=False), sa.Column("metrics", sa.JSON, nullable=False),
                    sa.Column("report_path", sa.String(400), nullable=False), sa.Column("created_at", TS, nullable=False))
    op.create_table("dataset_metadata",
                    sa.Column("id", sa.String(80), primary_key=True), sa.Column("name", sa.String(200), nullable=False),
                    sa.Column("url", sa.String(400), nullable=False), sa.Column("license", sa.String(300), nullable=False),
                    sa.Column("task_support", sa.String(300), nullable=False), sa.Column("status", sa.String(40), nullable=False),
                    sa.Column("details", sa.JSON, nullable=False))
    op.create_table("research_references",
                    sa.Column("id", sa.String(60), primary_key=True), sa.Column("title", sa.String(400), nullable=False),
                    sa.Column("authors", sa.String(400), nullable=False), sa.Column("year", sa.Integer, nullable=False),
                    sa.Column("venue", sa.String(200), nullable=False), sa.Column("doi_or_url", sa.String(300), nullable=False),
                    sa.Column("evidence_type", sa.String(8), nullable=False), sa.Column("relevance", sa.Text, nullable=False))
    op.create_table("activity_logs",
                    sa.Column("id", sa.Integer, primary_key=True),
                    sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
                    sa.Column("action", sa.String(60), nullable=False), sa.Column("entity", sa.String(40), nullable=False),
                    sa.Column("entity_id", sa.String(40), nullable=False), sa.Column("details", sa.JSON, nullable=False),
                    sa.Column("created_at", TS, nullable=False))
    op.create_index("ix_activity_logs_user_id", "activity_logs", ["user_id"])
    op.create_index("ix_activity_logs_action", "activity_logs", ["action"])
    op.create_index("ix_activity_logs_created_at", "activity_logs", ["created_at"])


def downgrade() -> None:
    for t in ("activity_logs", "research_references", "dataset_metadata", "evaluation_runs", "simulations",
              "pollination_records", "readiness_predictions", "maturity_predictions", "structure_detections",
              "flower_detections", "scans", "model_versions", "environment_records", "uploaded_images", "plants",
              "field_locations", "species", "users", "roles"):
        op.drop_table(t)
