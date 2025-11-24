from __future__ import annotations

import json
from typing import Optional
from pydantic import BaseModel, Field


class PensionVerification(BaseModel):
    """
    A class representing a TRS Retirement Allowance Verification / Pension Verification form.

    Attributes:
        Part B - Member/Beneficiary Info: Name, SSN, Address, Contact Information
        Part C - Attestation: Signatures, supporting documentation checkboxes
        Part D - Certification: Physician certification (Option 1) OR Notary acknowledgment (Option 2)
    """

    # Part B - Member / Beneficiary Info

    # Name Fields
    first_name: Optional[str] = Field(description="Member/beneficiary first name, e.g. Kevin, Maria")
    middle_initial: Optional[str] = Field(description="Member/beneficiary middle initial, e.g. T, A, L")
    last_name: Optional[str] = Field(description="Member/beneficiary last name, e.g. Johnson, Smith")

    # SSN
    ssn_last_four: Optional[str] = Field(description="Last four digits of SSN, e.g. 1234, 7890")

    # Address Fields
    permanent_home_address: Optional[str] = Field(description="Street address line, e.g. 123 Main St")
    apt_no: Optional[str] = Field(description="Apartment or unit number, e.g. Apt 5B, Unit 3F")
    city: Optional[str] = Field(description="City of permanent address, e.g. Brooklyn, Bronx")
    state: Optional[str] = Field(description="State of permanent address (2-letter), e.g. NY, NJ")
    zip_code: Optional[str] = Field(description="ZIP or ZIP+4 code, e.g. 11201, 10467-1234")

    # TRS Identifier
    trs_membership_retirement_number: Optional[str] = Field(description="TRS membership or retirement number, e.g. 07707290")

    # Contact Information
    primary_phone: Optional[str] = Field(description="Primary contact phone number, e.g. 212-555-0193")
    primary_phone_type: Optional[str] = Field(description="Phone type for primary number, e.g. Home, Work, Mobile")
    alternate_phone: Optional[str] = Field(description="Secondary contact phone number, e.g. 917-555-4402")
    alternate_phone_type: Optional[str] = Field(description="Phone type for alternate number, e.g. Home, Work, Mobile")
    email_address: Optional[str] = Field(description="Member/beneficiary email address, e.g. jsmith@example.com")

    # Contact Info Update Indicator
    new_contact_info_indicator: Optional[str] = Field(description="Checkbox showing contact info is new, e.g. Checked, Unchecked")

    # Part C - Attestation

    attestation_signed: Optional[str] = Field(description="Indicator that attestation section is signed, e.g. Yes, No")
    supporting_id_provided: Optional[str] = Field(description="Checkbox for gov't ID / Medicare / prescription statement, e.g. Checked, Unchecked")
    photo_with_newspaper_provided: Optional[str] = Field(description="Checkbox for photo with recent newspaper, e.g. Checked, Unchecked")
    agent_signing_indicator: Optional[str] = Field(description="Checkbox that signer is acting as agent, e.g. Checked, Unchecked")

    signer_signature: Optional[str] = Field(description="Signature in 'YOUR SIGNATURE' field")
    signer_printed_name: Optional[str] = Field(description="Printed name in 'YOUR PRINTED NAME' field")
    attestation_date: Optional[str] = Field(description="Date attestation signed (MM/DD/YYYY), e.g. 11/27/2023")

    # Part D - Physician Certification (Option 1)

    physician_name: Optional[str] = Field(description="Attending physician name, e.g. Dr. Karen Lee")
    physician_member_name: Optional[str] = Field(description="Member/beneficiary name in certification sentence, e.g. Kevin Johnson")
    physician_signature: Optional[str] = Field(description="Physician's signature")
    physician_signature_date: Optional[str] = Field(description="Date physician signs certification, e.g. 11/29/2023")
    physician_license_number: Optional[str] = Field(description="Physician license number, e.g. 123456, 0A98765")
    physician_license_state: Optional[str] = Field(description="State issuing the license, e.g. NY, NJ")

    # Part D - Notary Acknowledgment (Option 2)

    notary_state: Optional[str] = Field(description="State in 'State of ___', e.g. New York")
    notary_county: Optional[str] = Field(description="County in 'County of ___', e.g. Kings, Nassau")
    notary_acknowledgment_date: Optional[str] = Field(description="Date in 'On the __ day of ______ 20__', e.g. 11/29/2023")
    notary_member_name: Optional[str] = Field(description="Name of person appearing before notary, e.g. Kevin Johnson")
    notary_signature: Optional[str] = Field(description="Notary's signature")
    notary_commission_expiration_date: Optional[str] = Field(description="'Expiration Date of Commission' (MM/DD/YYYY), e.g. 05/13/2027")
    notary_official_title: Optional[str] = Field(description="Title in 'Official Title' field, e.g. Notary Public")

    @staticmethod
    def example():
        """
        Creates an example PensionVerification object with sample data.

        Returns:
            PensionVerification: An example PensionVerification object.
        """
        return PensionVerification(
            first_name="Kevin",
            middle_initial="T",
            last_name="Johnson",
            ssn_last_four="5677",
            permanent_home_address="123 Main St",
            apt_no="Apt 5B",
            city="Brooklyn",
            state="NY",
            zip_code="11201",
            trs_membership_retirement_number="07707290",
            primary_phone="212-555-0193",
            primary_phone_type="Home",
            email_address="kjohnson@example.com",
            attestation_date="11/27/2023"
        )

    @staticmethod
    def from_json(json_string: str) -> PensionVerification:
        """
        Creates a PensionVerification object from a JSON string.

        Args:
            json_string: JSON string representation of a PensionVerification

        Returns:
            PensionVerification: A PensionVerification object created from the JSON string
        """
        data = json.loads(json_string)
        return PensionVerification(**data)

    def to_dict(self):
        """
        Converts the PensionVerification object to a dictionary.

        Returns:
            dict: The PensionVerification object as a dictionary.
        """
        return {
            "first_name": self.first_name,
            "middle_initial": self.middle_initial,
            "last_name": self.last_name,
            "ssn_last_four": self.ssn_last_four,
            "permanent_home_address": self.permanent_home_address,
            "apt_no": self.apt_no,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "trs_membership_retirement_number": self.trs_membership_retirement_number,
            "primary_phone": self.primary_phone,
            "primary_phone_type": self.primary_phone_type,
            "alternate_phone": self.alternate_phone,
            "alternate_phone_type": self.alternate_phone_type,
            "email_address": self.email_address,
            "new_contact_info_indicator": self.new_contact_info_indicator,
            "attestation_signed": self.attestation_signed,
            "supporting_id_provided": self.supporting_id_provided,
            "photo_with_newspaper_provided": self.photo_with_newspaper_provided,
            "agent_signing_indicator": self.agent_signing_indicator,
            "signer_signature": self.signer_signature,
            "signer_printed_name": self.signer_printed_name,
            "attestation_date": self.attestation_date,
            "physician_name": self.physician_name,
            "physician_member_name": self.physician_member_name,
            "physician_signature": self.physician_signature,
            "physician_signature_date": self.physician_signature_date,
            "physician_license_number": self.physician_license_number,
            "physician_license_state": self.physician_license_state,
            "notary_state": self.notary_state,
            "notary_county": self.notary_county,
            "notary_acknowledgment_date": self.notary_acknowledgment_date,
            "notary_member_name": self.notary_member_name,
            "notary_signature": self.notary_signature,
            "notary_commission_expiration_date": self.notary_commission_expiration_date,
            "notary_official_title": self.notary_official_title
        }
