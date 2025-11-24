from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class IndexCard(BaseModel):
    """
    A class representing a Teachers' Retirement System Index Card.

    This schema extracts member information from scanned index cards containing
    employment, membership, and retirement information for TRS members.

    Attributes:
        last_name: Member's last name
        suffix: Member's name suffix
        first_name: Member's first name
        middle_initial: Member's middle initial
        header_maiden: Column heading for maiden name field
        maiden_name: Former last name of the member
        membership_number: Primary member identification number
        membership_number_2nd: Second identification number for members with gaps in service
        membership_number_extra: Extra identification number for members with multiple gaps
        withdrawal_number: ID number for withdrawn members
        withdrawal_number_2nd: Second withdrawal ID for members who withdrew multiple times
        retirement_number: ID number for retired members
        retirement_number_2nd: Second retirement ID for members who retired multiple times
        termination_number: ID number for terminated members
        school_name: Name of school where member teaches
        school_number: NYC public school number
        school_code: School identification code (borough-based)
        borough_brooklyn: Indicator that member teaches in Brooklyn
        borough_bronx: Indicator that member teaches in Bronx
        borough_manhattan: Indicator that member teaches in Manhattan
        borough_queens: Indicator that member teaches in Queens
        borough_richmond: Indicator that member teaches in Richmond
        header_birth: Column heading for birth date
        birth_date: Member's date of birth
        header_appointment: Column heading for appointment date
        appointment_date: Date member assigned teaching license
        header_retire_date: Column heading for retirement date
        retire_date: Date member retires from role
        header_resign: Column heading for resignation date
        resignation_date: Date member resigns from role
        header_died: Column heading for death date
        death_date: Date member dies
        header_membership_date: Column heading for membership enrollment date
        membership_date: Date member enrolled as TRS member
        header_reappd: Column heading for re-appointment date
        reappd_date: Date member re-appointed after termination/retirement/resignation
        header_serv_term: Column heading for service termination date
        serv_term_date: Date member's service is terminated
        header_licence_term: Column heading for license termination date
        license_term_date: Date member's teaching license is terminated
        header_term_rescind: Column heading for termination rescinded date
        term_rescind_date: Date member's termination was rescinded
        header_res_rescind: Column heading for resignation rescinded date
        resignation_rescinded_date: Date member's resignation was rescinded
        header_restored: Column heading for license restored date
        restored_date: Date member's teaching license is restored
        transfer_notes: Notes indicating member transfer
        transfer_date: Date member transfers to/from external school system
        boe_number: Board of Education identification number
        ssn: Member's Social Security Number
        header_boe: Column heading for BOE number
        header_ssn: Column heading for SSN
        notes: Any additional written text found on the index card
    """

    # Name Fields
    last_name: Optional[str] = Field(
        description="Member's last name, may be handwritten or typed, e.g. Johnson, Smith"
    )
    suffix: Optional[str] = Field(
        description="Member's name suffix, e.g. III, Jr., Sr."
    )
    first_name: Optional[str] = Field(
        description="Member's first name, may be handwritten or typed, e.g. Kevin, Joseph"
    )
    middle_initial: Optional[str] = Field(
        description="Member's middle initial, e.g. T., A., L."
    )
    header_maiden: Optional[str] = Field(
        description="Column heading for member maiden name field, e.g. Nee:"
    )
    maiden_name: Optional[str] = Field(
        description="Former last name of the member, e.g. Johnson, Smith"
    )

    # Membership Numbers
    membership_number: Optional[str] = Field(
        description="Primary member identification number, a six digit number starting with 0, 1, 2 OR 5, 6, 7, can start with '00T-', e.g. 026885, 00T026885"
    )
    membership_number_2nd: Optional[str] = Field(
        description="Second identification number for members who have gaps in service, found below the first membership number, e.g. 026885, 00T026885"
    )
    membership_number_extra: Optional[str] = Field(
        description="Any extra identification number for members who have multiple gaps in service, found below the second membership number, e.g. 026885, 00T026885"
    )
    withdrawal_number: Optional[str] = Field(
        description="Identification number given to members who withdraw their membership, starts with 'W' or 'W-' or 'W#' followed by 5 or 6 digits, e.g. W026885, W-026885, W#026885"
    )
    withdrawal_number_2nd: Optional[str] = Field(
        description="Second identification number given to members who have withdrawn membership multiple times, e.g. W026885, W-026885, W#026885"
    )
    retirement_number: Optional[str] = Field(
        description="Identification number given to members who retire, starts with 'R' or 'R-' followed by 5 digits, e.g. R37864, R-37864"
    )
    retirement_number_2nd: Optional[str] = Field(
        description="Second identification number for members who have retired more than once, e.g. R37864, R-37864"
    )
    termination_number: Optional[str] = Field(
        description="Identification number given to former members who were terminated, starts with 'T' followed by 5 digits, e.g. T85673, T-85673"
    )

    # School Information
    school_name: Optional[str] = Field(
        description="Name of school member teaches at, e.g. Abraham Lincoln HS, IS 7"
    )
    school_number: Optional[str] = Field(
        description="Number given to indicate the school number for the NYC public school the member teaches at, found to the left of county code, e.g. 117, 91, 15"
    )
    school_code: Optional[str] = Field(
        description="Identification number for each school in the NYC school system, starts with 'B' for Brooklyn, 'X' for Bronx, 'Q' for Queens, 'M' for Manhattan, 'R' for Richmond, e.g. B72, X130, R99, M117"
    )

    # Borough Indicators
    borough_brooklyn: Optional[str] = Field(
        description="Indicator that member teaches in Brooklyn, found to the right of School Name or School Number, e.g. Bkyln., Bk., Bkn., Brooklyn"
    )
    borough_bronx: Optional[str] = Field(
        description="Indicator that member teaches in Bronx, found to the right of School Name or School Number, e.g. Bronx, Bx."
    )
    borough_manhattan: Optional[str] = Field(
        description="Indicator that member teaches in Manhattan, found to the right of School Name or School Number, e.g. Man., Manhattan"
    )
    borough_queens: Optional[str] = Field(
        description="Indicator that member teaches in Queens, found to the right of School Name or School Number, e.g. Qns., Queens"
    )
    borough_richmond: Optional[str] = Field(
        description="Indicator that member teaches in Richmond, found to the right of School Name or School Number, e.g. Richmond, Rich."
    )

    # Birth Date
    header_birth: Optional[str] = Field(
        description="Column heading for member birth date, e.g. Birth Date:, D.O.B.:, Birth:, d.o.b:"
    )
    birth_date: Optional[str] = Field(
        description="Date of member's birth, found to the right of Header (Birth), in MM/DD/YY format, e.g. 11/27/62, 6/14/78"
    )

    # Appointment Date
    header_appointment: Optional[str] = Field(
        description="Column heading for member appointment date, e.g. Appd.:, Date appd.:, Appointment Date:"
    )
    appointment_date: Optional[str] = Field(
        description="Date member is assigned a teaching license, found to the right of Header (Appointment), in MM/DD/YY format, e.g. 11/27/62, 6/14/78"
    )

    # Retirement Date
    header_retire_date: Optional[str] = Field(
        description="Column heading for member retirement date, e.g. Ret.:, Retired:, Ret. Date:, Retire Date:"
    )
    retire_date: Optional[str] = Field(
        description="Date member retires from role, found to the right of Header (Retire Date), in MM/DD/YY format, e.g. 11/27/62, 6/14/75"
    )

    # Resignation Date
    header_resign: Optional[str] = Field(
        description="Column heading for member resignation date, e.g. Res.:, Resigned:, Res. Date:, Resign Date:"
    )
    resignation_date: Optional[str] = Field(
        description="Date member resigns from role, found to the right of Header (Resign), in MM/DD/YY format, e.g. 11/27/62, 6/14/75"
    )

    # Death Date
    header_died: Optional[str] = Field(
        description="Column heading for member death date, e.g. Died:, Death Date:"
    )
    death_date: Optional[str] = Field(
        description="Date member dies, found to the right of Header (Died), in MM/DD/YY format, e.g. 11/27/62, 6/14/75"
    )

    # Membership Date
    header_membership_date: Optional[str] = Field(
        description="Column heading for member membership enrollment date, e.g. Mem:, Date of Member:, Membership Date:"
    )
    membership_date: Optional[str] = Field(
        description="Date member is enrolled as a member of TRS, found to the right of Header (Membership Date), in MM/DD/YY format, e.g. 11/27/62, 6/14/75"
    )

    # Re-appointment Date
    header_reappd: Optional[str] = Field(
        description="Column heading for member re-appointment date, e.g. Re-appd:, Date re-appd.:, Re-appointment Date:"
    )
    reappd_date: Optional[str] = Field(
        description="Date member is re-appointed into a role after being terminated, retired, or resigning, found to the right of Header (Re-appd), in MM/DD/YY format, e.g. 11/27/62, 6/14/75"
    )

    # Service Termination Date
    header_serv_term: Optional[str] = Field(
        description="Column heading for member service termination date, e.g. Serv. Term:"
    )
    serv_term_date: Optional[str] = Field(
        description="Date member's service is terminated, found to the right of Header (Serv. Term), in MM/DD/YY format, e.g. 11/27/62, 6/14/75"
    )

    # License Termination Date
    header_licence_term: Optional[str] = Field(
        description="Column heading for member license termination date, e.g. Lic. Term:"
    )
    license_term_date: Optional[str] = Field(
        description="Date member's teaching license is terminated, found to the right of Header (License Term), in MM/DD/YY format, e.g. 11/27/62, 6/14/75"
    )

    # Termination Rescinded Date
    header_term_rescind: Optional[str] = Field(
        description="Column heading for date member's termination was rescinded, e.g. Term. Rescind:"
    )
    term_rescind_date: Optional[str] = Field(
        description="Date member has termination rescinded, found to the right of Header (Term. Rescind), in MM/DD/YY format, e.g. 11/27/62, 6/14/75"
    )

    # Resignation Rescinded Date
    header_res_rescind: Optional[str] = Field(
        description="Column heading for date member's resignation was rescinded, e.g. Res. Rescind:"
    )
    resignation_rescinded_date: Optional[str] = Field(
        description="Date member has resignation rescinded, found to the right of Header (Res. Rescind), in MM/DD/YY format, e.g. 11/27/62, 6/14/75"
    )

    # Restored Date
    header_restored: Optional[str] = Field(
        description="Column heading for date member's teaching license was restored, e.g. Rest:, Restored:"
    )
    restored_date: Optional[str] = Field(
        description="Date member's teaching license is restored, found to the right of Header (Restored), in MM/DD/YY format, e.g. 11/27/62, 6/14/75"
    )

    # Transfer Information
    transfer_notes: Optional[str] = Field(
        description="Notes indicating member transfer, could be a column heading, e.g. Transfer:, Transfer Date:, Transferred from XXXXX on"
    )
    transfer_date: Optional[str] = Field(
        description="Date member transfers to/from external school system, found to the right of Transfer Notes, in MM/DD/YY format, e.g. 11/27/62, 6/14/75"
    )

    # Identification Numbers
    boe_number: Optional[str] = Field(
        description="Board of Education identification number for members, does not change based on membership status"
    )
    ssn: Optional[str] = Field(
        description="Member's Social Security Number, 9 digits formatted XXX-XX-XXXX, e.g. 192-44-5677"
    )

    # Headers for ID Numbers
    header_boe: Optional[str] = Field(
        description="Column heading for member BOE number, e.g. BOE:, B.O.E.:, BOE#:"
    )
    header_ssn: Optional[str] = Field(
        description="Column heading for member social security number, e.g. SSN:, SS#:, S.S.N:"
    )

    # Additional Notes
    notes: Optional[str] = Field(
        description="Any additional written text found on the index card that doesn't fit into other categories"
    )

    @staticmethod
    def example():
        """
        Creates an example IndexCard object with sample data.

        Returns:
            IndexCard: An example IndexCard object.
        """
        return IndexCard(
            last_name="Johnson",
            suffix="Jr.",
            first_name="Kevin",
            middle_initial="T.",
            membership_number="026885",
            school_name="Abraham Lincoln HS",
            school_code="B72",
            borough_brooklyn="Brooklyn",
            birth_date="11/27/62",
            appointment_date="09/01/85",
            ssn="192-44-5677"
        )

    @staticmethod
    def from_json(json_string: str) -> IndexCard:
        """
        Creates an IndexCard object from a JSON string.

        Args:
            json_string: JSON string representation of an IndexCard

        Returns:
            IndexCard: An IndexCard object created from the JSON string
        """
        data = json.loads(json_string)
        return IndexCard(**data)

    def to_dict(self):
        """
        Converts the IndexCard object to a dictionary.

        Returns:
            dict: The IndexCard object as a dictionary.
        """
        return {
            "last_name": self.last_name,
            "suffix": self.suffix,
            "first_name": self.first_name,
            "middle_initial": self.middle_initial,
            "header_maiden": self.header_maiden,
            "maiden_name": self.maiden_name,
            "membership_number": self.membership_number,
            "membership_number_2nd": self.membership_number_2nd,
            "membership_number_extra": self.membership_number_extra,
            "withdrawal_number": self.withdrawal_number,
            "withdrawal_number_2nd": self.withdrawal_number_2nd,
            "retirement_number": self.retirement_number,
            "retirement_number_2nd": self.retirement_number_2nd,
            "termination_number": self.termination_number,
            "school_name": self.school_name,
            "school_number": self.school_number,
            "school_code": self.school_code,
            "borough_brooklyn": self.borough_brooklyn,
            "borough_bronx": self.borough_bronx,
            "borough_manhattan": self.borough_manhattan,
            "borough_queens": self.borough_queens,
            "borough_richmond": self.borough_richmond,
            "header_birth": self.header_birth,
            "birth_date": self.birth_date,
            "header_appointment": self.header_appointment,
            "appointment_date": self.appointment_date,
            "header_retire_date": self.header_retire_date,
            "retire_date": self.retire_date,
            "header_resign": self.header_resign,
            "resignation_date": self.resignation_date,
            "header_died": self.header_died,
            "death_date": self.death_date,
            "header_membership_date": self.header_membership_date,
            "membership_date": self.membership_date,
            "header_reappd": self.header_reappd,
            "reappd_date": self.reappd_date,
            "header_serv_term": self.header_serv_term,
            "serv_term_date": self.serv_term_date,
            "header_licence_term": self.header_licence_term,
            "license_term_date": self.license_term_date,
            "header_term_rescind": self.header_term_rescind,
            "term_rescind_date": self.term_rescind_date,
            "header_res_rescind": self.header_res_rescind,
            "resignation_rescinded_date": self.resignation_rescinded_date,
            "header_restored": self.header_restored,
            "restored_date": self.restored_date,
            "transfer_notes": self.transfer_notes,
            "transfer_date": self.transfer_date,
            "boe_number": self.boe_number,
            "ssn": self.ssn,
            "header_boe": self.header_boe,
            "header_ssn": self.header_ssn,
            "notes": self.notes
        }
