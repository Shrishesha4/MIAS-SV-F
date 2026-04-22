from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import relationship

from app.database import Base


lab_technician_group_labs = Table(
	"lab_technician_group_labs",
	Base.metadata,
	Column("group_id", String, ForeignKey("lab_technician_groups.id"), primary_key=True),
	Column("lab_id", String, ForeignKey("labs.id"), primary_key=True),
)


class LabTechnicianGroup(Base):
	__tablename__ = "lab_technician_groups"

	id = Column(String, primary_key=True)
	name = Column(String, nullable=False, unique=True, index=True)
	description = Column(Text, nullable=True)
	is_active = Column(Boolean, nullable=False, default=True)
	created_at = Column(DateTime, default=lambda: datetime.utcnow())
	updated_at = Column(
		DateTime,
		default=lambda: datetime.utcnow(),
		onupdate=lambda: datetime.utcnow(),
	)

	technicians = relationship("LabTechnician", back_populates="group")
	labs = relationship("Lab", secondary=lab_technician_group_labs)


class LabTechnician(Base):
	__tablename__ = "lab_technicians"

	id = Column(String, primary_key=True)
	technician_id = Column(String, unique=True, nullable=False, index=True)
	user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
	group_id = Column(String, ForeignKey("lab_technician_groups.id"), nullable=True, index=True)
	active_lab_id = Column(String, ForeignKey("labs.id"), nullable=True, index=True)
	name = Column(String, nullable=False)
	phone = Column(String, nullable=True)
	email = Column(String, nullable=True)
	photo = Column(String, nullable=True)
	department = Column(String, nullable=True)
	has_selected_lab = Column(Integer, nullable=False, default=0)
	last_checked_in_at = Column(DateTime, nullable=True)
	created_at = Column(DateTime, default=lambda: datetime.utcnow())
	updated_at = Column(
		DateTime,
		default=lambda: datetime.utcnow(),
		onupdate=lambda: datetime.utcnow(),
	)

	user = relationship("User", back_populates="lab_technician")
	group = relationship("LabTechnicianGroup", back_populates="technicians")
	active_lab = relationship("Lab")