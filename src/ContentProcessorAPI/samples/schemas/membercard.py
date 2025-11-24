from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MemberCard(BaseModel):
    """
    A class representing a member enrollment/retirement index card.

    This schema extracts key information from scanned index cards containing
    both handwritten and typed member information for the Teachers' Retirement System.

    Attributes:
        first_name: Member's first name
        last_name: Member's last name
        member_number: Unique member identification number
        date_of_birth: Member's date of birth
        enrollment_date: Date of enrollment, appointment, or when member joined
        school: School or institution where member was employed
        social_security_number: Member's SSN
        retirement_date: Date when member retired
    """

    first_name: Optional[str] = Field(
        description="Member's first name as it appears on the card, may be handwritten or typed, e.g. John"
    )
    last_name: Optional[str] = Field(
        description="Member's last name as it appears on the card, may be handwritten or typed, e.g. Smith"
    )
    member_number: Optional[str] = Field(
        description="Unique member identification number, may also be called member ID or account number, e.g. M123456"
    )
    date_of_birth: Optional[str] = Field(
        description="Member's date of birth in MM/DD/YYYY format, e.g. 01/15/1965"
    )
    enrollment_date: Optional[str] = Field(
        description="Date of enrollment, appointment date, or date member joined the system. May be labeled as 'Enrollment Date', 'Appointment Date', or 'Date of Enrollment'. Format: MM/DD/YYYY, e.g. 09/01/1990"
    )
    school: Optional[str] = Field(
        description="Name of the school or institution where the member was employed, e.g. PS 123, Brooklyn High School"
    )
    social_security_number: Optional[str] = Field(
        description="Member's Social Security Number in XXX-XX-XXXX format, e.g. 123-45-6789"
    )
    retirement_date: Optional[str] = Field(
        description="Date when the member retired from service in MM/DD/YYYY format, e.g. 06/30/2020. May be empty if member is still active."
    )

    @staticmethod
    def example():
        """
        Creates an example MemberCard object with sample data.

        Returns:
            MemberCard: An example MemberCard object.
        """
        return MemberCard(
            first_name="John",
            last_name="Smith",
            member_number="M123456",
            date_of_birth="01/15/1965",
            enrollment_date="09/01/1990",
            school="PS 123",
            social_security_number="123-45-6789",
            retirement_date="06/30/2020"
        )

    @staticmethod
    def from_json(json_string: str) -> MemberCard:
        """
        Creates a MemberCard object from a JSON string.

        Args:
            json_string: JSON string representation of a MemberCard

        Returns:
            MemberCard: A MemberCard object created from the JSON string
        """
        data = json.loads(json_string)
        return MemberCard(**data)

    def to_dict(self):
        """
        Converts the MemberCard object to a dictionary.

        Returns:
            dict: The MemberCard object as a dictionary.
        """
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "member_number": self.member_number,
            "date_of_birth": self.date_of_birth,
            "enrollment_date": self.enrollment_date,
            "school": self.school,
            "social_security_number": self.social_security_number,
            "retirement_date": self.retirement_date
        }
