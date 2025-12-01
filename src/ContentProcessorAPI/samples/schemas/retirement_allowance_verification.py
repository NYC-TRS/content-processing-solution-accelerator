from __future__ import annotations

import json
from typing import Optional
from pydantic import BaseModel, Field


class RetirementAllowanceVerificationForm(BaseModel):
    """
    A class representing a TRS Retirement Allowance Verification Form.

    This form verifies that a disability retiree remains disabled and unable to perform duties.

    Attributes:
        Member Information: Name, TRS ID, Address, Contact Information
        Physician Certification: Physician details, license, signature, certification statement
        Notary Acknowledgment (if applicable): Alternative to physician certification
    """

    # Member / Beneficiary Information

    # Name Fields
    first_name: Optional[str] = Field(description="Member/beneficiary first name, e.g. Teresa, John")
    middle_initial: Optional[str] = Field(description="Member/beneficiary middle initial, e.g. A, M")
    last_name: Optional[str] = Field(description="Member/beneficiary last name, e.g. Alejandro, Smith")

    # TRS Identifier
    trs_membership_retirement_number: Optional[str] = Field(
        description="TRS membership or retirement number, e.g. 004751633, 07707290"
    )

    # Address Fields
    permanent_home_address: Optional[str] = Field(
        description="Street address line, e.g. 123 Main St, 456 Broadway"
    )
    apt_no: Optional[str] = Field(
        description="Apartment or unit number, e.g. Apt 5B, Unit 3F"
    )
    city: Optional[str] = Field(
        description="City of permanent address, e.g. Brooklyn, Queens, Bronx"
    )
    state: Optional[str] = Field(
        description="State of permanent address (2-letter code), e.g. NY, NJ"
    )
    zip_code: Optional[str] = Field(
        description="ZIP or ZIP+4 code, e.g. 11201, 10467-1234"
    )

    # SSN
    ssn_last_four: Optional[str] = Field(
        description="Last four digits of Social Security Number, e.g. 1234, 5678"
    )

    # Contact Information
    primary_phone: Optional[str] = Field(
        description="Primary contact phone number, e.g. 212-555-0193, (718) 555-4402"
    )
    primary_phone_type: Optional[str] = Field(
        description="Phone type for primary number, e.g. Home, Work, Mobile, Cell"
    )
    alternate_phone: Optional[str] = Field(
        description="Secondary contact phone number, e.g. 917-555-4402"
    )
    alternate_phone_type: Optional[str] = Field(
        description="Phone type for alternate number, e.g. Home, Work, Mobile, Cell"
    )
    email_address: Optional[str] = Field(
        description="Member/beneficiary email address, e.g. talej@example.com"
    )

    # Physician Certification Section

    physician_name: Optional[str] = Field(
        description="Attending physician full name, e.g. Dr. Natalia Polyakova, Karen Lee MD"
    )
    physician_printed_name: Optional[str] = Field(
        description="Physician's printed name if separate from signature, e.g. Natalia Polyakova"
    )
    physician_signature: Optional[str] = Field(
        description="Physician's signature (indicates if signature is present)"
    )
    physician_signature_date: Optional[str] = Field(
        description="Date physician signed certification (MM/DD/YYYY), e.g. 11/14/2023, 2023-11-14"
    )
    physician_license_number: Optional[str] = Field(
        description="Physician state medical license number, e.g. 262562, NY-123456"
    )
    physician_license_state: Optional[str] = Field(
        description="State that issued the physician's medical license (2-letter code), e.g. NY, NJ, CA"
    )
    physician_npi: Optional[str] = Field(
        description="National Provider Identifier (NPI) number, 10-digit number, e.g. 1578718920"
    )
    physician_specialty: Optional[str] = Field(
        description="Medical specialty of physician, e.g. Internal Medicine, Psychiatry, Orthopedics"
    )
    physician_address: Optional[str] = Field(
        description="Full address of physician's office or medical practice, e.g. 1010 Central Park Ave, Yonkers, NY 10704"
    )
    physician_phone: Optional[str] = Field(
        description="Physician's office phone number, e.g. (914) 964-4127, 914-964-4127"
    )
    physician_fax: Optional[str] = Field(
        description="Physician's office fax number, e.g. (914) 964-4067"
    )

    # Certification Statement / Disability Status
    certification_statement: Optional[str] = Field(
        description="Full text of physician's certification statement, e.g. 'I certify that [member name] continues to be disabled and unable to perform their duties as a teacher'"
    )
    disability_status: Optional[str] = Field(
        description="Checkbox or statement about disability status, e.g. 'Continues to be disabled', 'Unable to work', 'Permanently disabled'"
    )
    disability_diagnosis: Optional[str] = Field(
        description="Medical diagnosis or condition if stated, e.g. 'Chronic back pain', 'Major depression'"
    )
    disability_start_date: Optional[str] = Field(
        description="Date disability began or was diagnosed, e.g. 01/15/2022"
    )

    # Notary Acknowledgment Section (if form has notary option)

    notary_state: Optional[str] = Field(
        description="State in 'State of ___' for notary section, e.g. New York"
    )
    notary_county: Optional[str] = Field(
        description="County in 'County of ___' for notary section, e.g. Kings, Queens, New York"
    )
    notary_acknowledgment_date: Optional[str] = Field(
        description="Date in notary acknowledgment, e.g. 11/14/2023"
    )
    notary_member_name: Optional[str] = Field(
        description="Name of person appearing before notary"
    )
    notary_signature: Optional[str] = Field(
        description="Notary's signature (indicates if notary signature is present)"
    )
    notary_commission_expiration_date: Optional[str] = Field(
        description="Notary commission expiration date (MM/DD/YYYY), e.g. 05/13/2027"
    )
    notary_commission_number: Optional[str] = Field(
        description="Notary commission number, e.g. 01DO1234567"
    )
    notary_official_title: Optional[str] = Field(
        description="Notary's official title, e.g. Notary Public"
    )

    # Form Metadata
    form_date: Optional[str] = Field(
        description="Date printed on form or form revision date, e.g. Rev. 2023, 01/2023"
    )
    form_number: Optional[str] = Field(
        description="Form number or identifier if present, e.g. TRS-804, Form 21B"
    )

    @staticmethod
    def example():
        """
        Creates an example RetirementAllowanceVerificationForm object with sample data.

        Returns:
            RetirementAllowanceVerificationForm: An example form object.
        """
        return RetirementAllowanceVerificationForm(
            first_name="Teresa",
            middle_initial="",
            last_name="Alejandro",
            trs_membership_retirement_number="004751633",
            permanent_home_address="123 Main St",
            city="Brooklyn",
            state="NY",
            zip_code="11201",
            primary_phone="212-555-0193",
            email_address="talej@example.com",
            physician_name="Natalia Polyakova",
            physician_signature_date="11/14/2023",
            physician_license_number="262562",
            physician_license_state="NY"
        )

    @staticmethod
    def from_json(json_string: str) -> RetirementAllowanceVerificationForm:
        """
        Creates a RetirementAllowanceVerificationForm object from a JSON string.

        Args:
            json_string: JSON string representation of the form

        Returns:
            RetirementAllowanceVerificationForm: Form object created from the JSON string
        """
        data = json.loads(json_string)
        return RetirementAllowanceVerificationForm(**data)

    def to_dict(self):
        """
        Converts the RetirementAllowanceVerificationForm object to a dictionary.

        Returns:
            dict: The form object as a dictionary.
        """
        return {
            "first_name": self.first_name,
            "middle_initial": self.middle_initial,
            "last_name": self.last_name,
            "trs_membership_retirement_number": self.trs_membership_retirement_number,
            "permanent_home_address": self.permanent_home_address,
            "apt_no": self.apt_no,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "ssn_last_four": self.ssn_last_four,
            "primary_phone": self.primary_phone,
            "primary_phone_type": self.primary_phone_type,
            "alternate_phone": self.alternate_phone,
            "alternate_phone_type": self.alternate_phone_type,
            "email_address": self.email_address,
            "physician_name": self.physician_name,
            "physician_printed_name": self.physician_printed_name,
            "physician_signature": self.physician_signature,
            "physician_signature_date": self.physician_signature_date,
            "physician_license_number": self.physician_license_number,
            "physician_license_state": self.physician_license_state,
            "physician_npi": self.physician_npi,
            "physician_specialty": self.physician_specialty,
            "physician_address": self.physician_address,
            "physician_phone": self.physician_phone,
            "physician_fax": self.physician_fax,
            "certification_statement": self.certification_statement,
            "disability_status": self.disability_status,
            "disability_diagnosis": self.disability_diagnosis,
            "disability_start_date": self.disability_start_date,
            "notary_state": self.notary_state,
            "notary_county": self.notary_county,
            "notary_acknowledgment_date": self.notary_acknowledgment_date,
            "notary_member_name": self.notary_member_name,
            "notary_signature": self.notary_signature,
            "notary_commission_expiration_date": self.notary_commission_expiration_date,
            "notary_commission_number": self.notary_commission_number,
            "notary_official_title": self.notary_official_title,
            "form_date": self.form_date,
            "form_number": self.form_number
        }
