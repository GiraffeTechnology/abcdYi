"""Approval-gate binding + replay-protection tests (security P0 #1).

A human approval must only authorise the exact action it was created for:
the action_type, resource and tenant must all match, and an approval can be
spent at most once. These tests prove an approved request cannot be replayed
against a different resource, a different action, or twice.
"""
import pytest


async def _create_rfq(auth_client, project, participants):
    resp = await auth_client.post(
        f"/api/projects/{project['id']}/rfqs",
        json={
            "form_version_id": project["form_version_id"],
            "recipient_participant_ids": [participants[0]["id"]],
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return data["rfq"]["id"], data["approval_request_id"]


@pytest.mark.asyncio
async def test_approval_bound_to_its_resource(
    auth_client, seed_project_with_form, seed_participants
):
    """An approval granted for RFQ #1 cannot authorise sending RFQ #2."""
    rfq1_id, approval1_id = await _create_rfq(auth_client, seed_project_with_form, seed_participants)
    rfq2_id, _approval2_id = await _create_rfq(auth_client, seed_project_with_form, seed_participants)

    # Approve only approval #1
    await auth_client.post(
        f"/api/approval-requests/{approval1_id}/approve",
        json={"review_notes": "ok"},
    )

    # Replay approval #1 against RFQ #2 -> rejected
    resp = await auth_client.post(
        f"/api/rfqs/{rfq2_id}/send",
        json={"approval_id": approval1_id},
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_approval_is_consumed_once(auth_client, seed_rfq):
    """An approval cannot be replayed after it has been spent."""
    approval_id = seed_rfq["approval_request_id"]
    await auth_client.post(
        f"/api/approval-requests/{approval_id}/approve",
        json={"review_notes": "ok"},
    )

    # First send succeeds
    first = await auth_client.post(
        f"/api/rfqs/{seed_rfq['id']}/send",
        json={"approval_id": approval_id},
    )
    assert first.status_code == 200, first.text

    # Replaying the now-consumed approval is rejected
    second = await auth_client.post(
        f"/api/rfqs/{seed_rfq['id']}/send",
        json={"approval_id": approval_id},
    )
    assert second.status_code == 403, second.text


@pytest.mark.asyncio
async def test_approval_action_type_must_match(
    auth_client, seed_decision_packet, seed_project_with_form, seed_participants
):
    """A QUOTE_APPROVE approval cannot authorise an RFQ_SEND action."""
    rfq_id, _ = await _create_rfq(auth_client, seed_project_with_form, seed_participants)
    quote_approval_id = seed_decision_packet["approval_request_id"]

    # Approve the QUOTE_APPROVE approval
    await auth_client.post(
        f"/api/approval-requests/{quote_approval_id}/approve",
        json={"review_notes": "ok"},
    )

    # Use it to try to send an RFQ -> action_type mismatch -> rejected
    resp = await auth_client.post(
        f"/api/rfqs/{rfq_id}/send",
        json={"approval_id": quote_approval_id},
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_correctly_bound_approval_still_works(auth_client, seed_rfq):
    """Happy path: a matching, approved, unconsumed approval authorises the action."""
    approval_id = seed_rfq["approval_request_id"]
    await auth_client.post(
        f"/api/approval-requests/{approval_id}/approve",
        json={"review_notes": "ok"},
    )
    resp = await auth_client.post(
        f"/api/rfqs/{seed_rfq['id']}/send",
        json={"approval_id": approval_id},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "SENT"
