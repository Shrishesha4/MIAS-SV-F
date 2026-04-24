"""add academics configuration

Revision ID: 20260424_0040
Revises: 20260424_0039, 20260424_0038b
Create Date: 2026-04-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260424_0040"
down_revision = ("20260424_0039", "20260424_0038b")
branch_labels = None
depends_on = None


def _get_table_names(bind) -> set[str]:
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def _get_column_names(bind, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def _get_index_names(bind, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _get_unique_constraint_names(bind, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    return {
        constraint["name"]
        for constraint in inspector.get_unique_constraints(table_name)
        if constraint.get("name")
    }


def _get_foreign_key_names(bind, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    return {
        fk["name"] for fk in inspector.get_foreign_keys(table_name) if fk.get("name")
    }


def upgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)

    if "academic_groups" not in tables:
        op.create_table(
            "academic_groups",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("programme_id", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(["programme_id"], ["programmes.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "programme_id", "name", name="uq_academic_groups_programme_name"
            ),
        )

    tables = _get_table_names(bind)
    if "academic_targets" not in tables:
        op.create_table(
            "academic_targets",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("group_id", sa.String(), nullable=False),
            sa.Column("form_definition_id", sa.String(), nullable=True),
            sa.Column("metric_name", sa.String(), nullable=False),
            sa.Column(
                "category", sa.String(), nullable=False, server_default="ACADEMIC"
            ),
            sa.Column("target_value", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(["form_definition_id"], ["form_definitions.id"]),
            sa.ForeignKeyConstraint(["group_id"], ["academic_groups.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    tables = _get_table_names(bind)
    if "academic_form_weightages" not in tables:
        op.create_table(
            "academic_form_weightages",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("form_definition_id", sa.String(), nullable=False),
            sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(["form_definition_id"], ["form_definitions.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "form_definition_id", name="uq_academic_form_weightages_form_definition"
            ),
        )

    tables = _get_table_names(bind)
    if "students" in tables:
        student_columns = _get_column_names(bind, "students")
        if "academic_group_id" not in student_columns:
            op.add_column(
                "students", sa.Column("academic_group_id", sa.String(), nullable=True)
            )

        student_fk_names = _get_foreign_key_names(bind, "students")
        if "fk_students_academic_group_id" not in student_fk_names:
            op.create_foreign_key(
                "fk_students_academic_group_id",
                "students",
                "academic_groups",
                ["academic_group_id"],
                ["id"],
            )

    academic_group_indexes = (
        _get_index_names(bind, "academic_groups")
        if "academic_groups" in _get_table_names(bind)
        else set()
    )
    if "ix_academic_groups_programme_id" not in academic_group_indexes:
        op.create_index(
            "ix_academic_groups_programme_id",
            "academic_groups",
            ["programme_id"],
            unique=False,
        )
    if "idx_academic_groups_programme_active" not in academic_group_indexes:
        op.create_index(
            "idx_academic_groups_programme_active",
            "academic_groups",
            ["programme_id", "is_active"],
            unique=False,
        )

    academic_target_indexes = (
        _get_index_names(bind, "academic_targets")
        if "academic_targets" in _get_table_names(bind)
        else set()
    )
    if "ix_academic_targets_group_id" not in academic_target_indexes:
        op.create_index(
            "ix_academic_targets_group_id",
            "academic_targets",
            ["group_id"],
            unique=False,
        )
    if "ix_academic_targets_form_definition_id" not in academic_target_indexes:
        op.create_index(
            "ix_academic_targets_form_definition_id",
            "academic_targets",
            ["form_definition_id"],
            unique=False,
        )
    if "idx_academic_targets_group_sort" not in academic_target_indexes:
        op.create_index(
            "idx_academic_targets_group_sort",
            "academic_targets",
            ["group_id", "sort_order"],
            unique=False,
        )
    if "idx_academic_targets_group_category" not in academic_target_indexes:
        op.create_index(
            "idx_academic_targets_group_category",
            "academic_targets",
            ["group_id", "category"],
            unique=False,
        )

    weightage_indexes = (
        _get_index_names(bind, "academic_form_weightages")
        if "academic_form_weightages" in _get_table_names(bind)
        else set()
    )
    if "ix_academic_form_weightages_form_definition_id" not in weightage_indexes:
        op.create_index(
            "ix_academic_form_weightages_form_definition_id",
            "academic_form_weightages",
            ["form_definition_id"],
            unique=False,
        )

    if "students" in _get_table_names(bind):
        student_indexes = _get_index_names(bind, "students")
        if "ix_students_academic_group_id" not in student_indexes:
            op.create_index(
                "ix_students_academic_group_id",
                "students",
                ["academic_group_id"],
                unique=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    tables = _get_table_names(bind)

    if "students" in tables:
        student_indexes = _get_index_names(bind, "students")
        if "ix_students_academic_group_id" in student_indexes:
            op.drop_index("ix_students_academic_group_id", table_name="students")

        student_columns = _get_column_names(bind, "students")
        student_fk_names = _get_foreign_key_names(bind, "students")
        if (
            "academic_group_id" in student_columns
            and "fk_students_academic_group_id" in student_fk_names
        ):
            op.drop_constraint(
                "fk_students_academic_group_id", "students", type_="foreignkey"
            )
        if "academic_group_id" in student_columns:
            op.drop_column("students", "academic_group_id")

    tables = _get_table_names(bind)
    if "academic_form_weightages" in tables:
        weightage_indexes = _get_index_names(bind, "academic_form_weightages")
        if "ix_academic_form_weightages_form_definition_id" in weightage_indexes:
            op.drop_index(
                "ix_academic_form_weightages_form_definition_id",
                table_name="academic_form_weightages",
            )
        op.drop_table("academic_form_weightages")

    tables = _get_table_names(bind)
    if "academic_targets" in tables:
        academic_target_indexes = _get_index_names(bind, "academic_targets")
        if "idx_academic_targets_group_category" in academic_target_indexes:
            op.drop_index(
                "idx_academic_targets_group_category", table_name="academic_targets"
            )
        if "idx_academic_targets_group_sort" in academic_target_indexes:
            op.drop_index(
                "idx_academic_targets_group_sort", table_name="academic_targets"
            )
        if "ix_academic_targets_form_definition_id" in academic_target_indexes:
            op.drop_index(
                "ix_academic_targets_form_definition_id", table_name="academic_targets"
            )
        if "ix_academic_targets_group_id" in academic_target_indexes:
            op.drop_index("ix_academic_targets_group_id", table_name="academic_targets")
        op.drop_table("academic_targets")

    tables = _get_table_names(bind)
    if "academic_groups" in tables:
        academic_group_indexes = _get_index_names(bind, "academic_groups")
        if "idx_academic_groups_programme_active" in academic_group_indexes:
            op.drop_index(
                "idx_academic_groups_programme_active", table_name="academic_groups"
            )
        if "ix_academic_groups_programme_id" in academic_group_indexes:
            op.drop_index(
                "ix_academic_groups_programme_id", table_name="academic_groups"
            )
        op.drop_table("academic_groups")
