"""Shared fixtures for the acmt001-lsp test suite."""

import pytest

_RECORD = {
    "msg_id": "ACMT-MSG-0001",
    "creation_date_time": "2026-01-15T10:30:00",
    "process_id": "ACMT-PRC-0001",
    "account_id": "GB29NWBK60161331926819",
    "account_id_other": "VRTL-0001-0001",
    "account_currency": "EUR",
    "account_name": "Treasury Operating Account",
    "account_type_cd": "CACC",
    "account_servicer_bic": "NWBKGB2LXXX",
    "account_owner_name": "Acme Embedded Finance Ltd",
    "account_owner_country": "GB",
    "account_owner_lei": "5493001KJTIIGC8Y1R12",
    "org_full_legal_name": "Acme Embedded Finance Limited",
    "org_country_of_operation": "GB",
    "org_address_country": "GB",
    "org_address_town": "London",
    "org_id_lei": "5493001KJTIIGC8Y1R12",
    "org_id_other": "ACME-ORG-001",
    "status_cd": "RECE",
    "reason_cd": "RR04",
    "additional_info": "Onboarding via BaaS platform",
    "assigner_name": "Acme Embedded Finance Ltd",
    "assignee_name": "National Westminster Bank",
    "verification_id": "VRFY-0001",
    "party_name": "Acme Embedded Finance Ltd",
    "verification_indicator": "true",
    "original_id": "VRFY-0001",
    "request_to_be_completed_id": "ACMT-REQ-0007",
    "request_reason": "KYC documentation outstanding",
    "mandate_id": "MNDT-0001",
    "mandate_channel": "ONLINE_BANKING",
    "required_signature_number": "2",
    "signature_order_indicator": "false",
    "switch_reference": "SWTCH-0001",
    "routing_id": "RTNG-0001",
    "new_account_id": "GB94BARC10201530093459",
    "new_account_servicer_bic": "BARCGB22XXX",
    "old_account_id": "GB29NWBK60161331926819",
    "old_account_servicer_bic": "NWBKGB2LXXX",
    "account_owner_surname": "Rousseau",
    "account_owner_given_name": "Sebastian",
}


@pytest.fixture
def sample_record() -> dict:
    """A complete account record satisfying every acmt message type."""
    return dict(_RECORD)
