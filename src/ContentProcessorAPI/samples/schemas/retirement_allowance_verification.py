from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class PhysicianSignature(BaseModel):
    """
    A class representing a physician signature.

    Attributes:
        signatory: Name of the physician who signed.
        is_signed: Indicates if the form is signed.
    """

    signatory: Optional[str] = Field(
        description="Name of the physician who signed the form"
    )
    is_signed: Optional[bool] = Field(
        description="Indicates if the form is signed. Check whether there is a signature in the image."
    )

    @staticmethod
    def example():
        """
        Creates an empty example PhysicianSignature object.

        Returns:
            PhysicianSignature: An empty PhysicianSignature object.
        """
        return PhysicianSignature(signatory="", is_signed=False)

    def to_dict(self):
        """
        Converts the PhysicianSignature object to a dictionary.

        Returns:
            dict: The PhysicianSignature object as a dictionary.
        """
        return {"signatory": self.signatory, "is_signed": self.is_signed}


class RetirementAllowanceVerificationForm(BaseModel):
    """
    A class representing a Teachers' Retirement System (TRS) Retirement Allowance Verification Form.

    This form is used to verify that a retiree remains disabled and unable to perform their duties.
    It must be completed by a licensed physician.

    Attributes:
        member_name: Full name of the TRS member/retiree.
        member_id: TRS member identification number (if present on form).
        physician_name: Full name of the examining physician.
        physician_npi: National Provider Identifier (NPI) number of the physician.
        physician_license_number: State medical license number of the physician.
        state_issuing_license: State that issued the physician's medical license (e.g., CA, NY, TX).
        physician_signature: Signature of the physician.
        verification_date: Date the physician signed/verified the form.
        disability_status: Statement or checkbox indicating the member's disability status.
        physician_address: Address of the physician or medical practice.
        physician_phone: Phone number of the physician or medical practice.
    """

    member_name: Optional[str] = Field(
        description="Full name of the TRS member/retiree, e.g. John Smith"
    )
    member_id: Optional[str] = Field(
        description="TRS member identification number, if present on the form"
    )
    physician_name: Optional[str] = Field(
        description="Full name of the examining physician, e.g. Dr. Jane Doe"
    )
    physician_npi: Optional[str] = Field(
        description="National Provider Identifier (NPI) number of the physician, a 10-digit number, e.g. 1234567890"
    )
    physician_license_number: Optional[str] = Field(
        description="State medical license number of the physician"
    )
    state_issuing_license: Optional[str] = Field(
        description="State that issued the physician's medical license (two-letter code), e.g. CA, NY, TX"
    )
    physician_signature: Optional[PhysicianSignature] = Field(
        description="Signature of the physician who completed the verification"
    )
    verification_date: Optional[str] = Field(
        description="Date the physician signed/verified the form, e.g. 2023-01-01"
    )
    disability_status: Optional[str] = Field(
        description="Statement or checkbox value indicating the member's current disability status"
    )
    physician_address: Optional[str] = Field(
        description="Full address of the physician or medical practice"
    )
    physician_phone: Optional[str] = Field(
        description="Phone number of the physician or medical practice, e.g. (555) 123-4567"
    )

    @staticmethod
    def example():
        """
        Creates an empty example RetirementAllowanceVerificationForm object.

        Returns:
            RetirementAllowanceVerificationForm: An empty RetirementAllowanceVerificationForm object.
        """
        return RetirementAllowanceVerificationForm(
            member_name="",
            member_id="",
            physician_name="",
            physician_npi="",
            physician_license_number="",
            state_issuing_license="",
            physician_signature=PhysicianSignature.example(),
            verification_date="",
            disability_status="",
            physician_address="",
            physician_phone="",
        )

    def to_dict(self):
        """
        Converts the RetirementAllowanceVerificationForm object to a dictionary.

        Returns:
            dict: The RetirementAllowanceVerificationForm object as a dictionary.
        """
        return {
            "member_name": self.member_name,
            "member_id": self.member_id,
            "physician_name": self.physician_name,
            "physician_npi": self.physician_npi,
            "physician_license_number": self.physician_license_number,
            "state_issuing_license": self.state_issuing_license,
            "physician_signature": self.physician_signature.to_dict()
            if self.physician_signature is not None
            else None,
            "verification_date": self.verification_date,
            "disability_status": self.disability_status,
            "physician_address": self.physician_address,
            "physician_phone": self.physician_phone,
        }
