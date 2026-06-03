from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.core.token_hashing import hash_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.agent import Agent
from app.models.audit_log import AuditLog
from app.models.device import Device
from app.models.device_checkin import DeviceCheckin
from app.models.device_inventory import DeviceInventory
from app.models.enrollment_token import EnrollmentToken
from app.models.installed_software import InstalledSoftware
from app.models.organization import Organization
from app.models.user import User


@pytest.fixture()
def db() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()

    def override_get_db() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield session
    finally:
        app.dependency_overrides.clear()
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db: Session) -> TestClient:
    return TestClient(app)


def create_org(db: Session) -> Organization:
    org = Organization(name="Acme MSP", slug="acme")
    db.add(org)
    db.commit()
    return org


def auth_headers(
    db: Session, org: Organization, *, role: str = "owner", email: str | None = None
) -> dict[str, str]:
    user = User(
        organization_id=org.id,
        email=email or f"{role}-{org.slug}@example.test",
        hashed_password=hash_password("CorrectHorseBatteryStaple!1"),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    response = TestClient(app).post(
        "/api/auth/login",
        json={"email": user.email, "password": "CorrectHorseBatteryStaple!1"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_enrollment_token(
    db: Session,
    org: Organization,
    token: str = "enroll-token-value-123456",
    *,
    expires_delta: timedelta = timedelta(hours=1),
    max_uses: int = 1,
    uses: int = 0,
    revoked: bool = False,
) -> EnrollmentToken:
    enrollment_token = EnrollmentToken(
        organization_id=org.id,
        token_hash=hash_token(token),
        expires_at=datetime.now(UTC) + expires_delta,
        max_uses=max_uses,
        uses=uses,
        revoked_at=datetime.now(UTC) if revoked else None,
    )
    db.add(enrollment_token)
    db.commit()
    return enrollment_token


def enroll_payload(token: str = "enroll-token-value-123456") -> dict[str, str]:
    return {
        "enrollment_token": token,
        "hostname": "WIN-01",
        "operating_system": "Windows 11 Pro",
        "architecture": "amd64",
        "agent_version": "0.2.0",
        "machine_identifier": "machine-guid-001",
    }


def test_enrollment_success_creates_device_agent_and_audit_log(
    client: TestClient, db: Session
) -> None:
    org = create_org(db)
    client.headers.update(auth_headers(db, org))
    token = create_enrollment_token(db, org)

    response = client.post("/api/agent/enroll", json=enroll_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["device_id"]
    assert body["device_secret"]
    assert body["device_secret"] not in {token.token_hash}

    device = db.get(Device, UUID(body["device_id"]))
    assert device is not None
    assert device.organization_id == org.id
    assert device.hostname == "WIN-01"
    assert device.status == "online"
    assert device.last_seen_at is not None

    agent = db.scalar(select(Agent).where(Agent.device_id == device.id))
    assert agent is not None
    assert agent.device_secret_hash != body["device_secret"]

    db.refresh(token)
    assert token.uses == 1
    audit = db.scalar(select(AuditLog).where(AuditLog.action == "agent.enrolled"))
    assert audit is not None
    assert audit.target_id == str(device.id)


def test_expired_enrollment_token_is_rejected(client: TestClient, db: Session) -> None:
    org = create_org(db)
    client.headers.update(auth_headers(db, org))
    create_enrollment_token(db, org, expires_delta=timedelta(seconds=-1))

    response = client.post("/api/agent/enroll", json=enroll_payload())

    assert response.status_code == 401
    assert db.scalar(select(Device)) is None


def test_revoked_enrollment_token_is_rejected(client: TestClient, db: Session) -> None:
    org = create_org(db)
    client.headers.update(auth_headers(db, org))
    create_enrollment_token(db, org, revoked=True)

    response = client.post("/api/agent/enroll", json=enroll_payload())

    assert response.status_code == 401
    assert db.scalar(select(Device)) is None


def test_max_usage_enrollment_token_is_rejected(client: TestClient, db: Session) -> None:
    org = create_org(db)
    client.headers.update(auth_headers(db, org))
    create_enrollment_token(db, org, max_uses=1, uses=1)

    response = client.post("/api/agent/enroll", json=enroll_payload())

    assert response.status_code == 401
    assert db.scalar(select(Device)) is None


def test_failed_device_auth_uses_generic_error(client: TestClient, db: Session) -> None:
    org = create_org(db)
    client.headers.update(auth_headers(db, org))
    create_enrollment_token(db, org)
    enroll = client.post("/api/agent/enroll", json=enroll_payload()).json()

    response = client.post(
        "/api/agent/checkin",
        json={
            "device_id": enroll["device_id"],
            "device_secret": "wrong-device-secret-123456",
            "hostname": "WIN-01",
            "operating_system": "Windows 11 Pro",
            "architecture": "amd64",
            "agent_version": "0.2.0",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid device credentials"


def test_successful_checkin_updates_device_and_records_audit(
    client: TestClient, db: Session
) -> None:
    org = create_org(db)
    client.headers.update(auth_headers(db, org))
    create_enrollment_token(db, org)
    enroll = client.post("/api/agent/enroll", json=enroll_payload()).json()

    response = client.post(
        "/api/agent/checkin",
        json={
            "device_id": enroll["device_id"],
            "device_secret": enroll["device_secret"],
            "hostname": "WIN-01-RENAMED",
            "operating_system": "Windows 11 Pro",
            "architecture": "amd64",
            "agent_version": "0.2.1",
            "ip_address": "10.0.0.15",
            "local_ips": ["10.0.0.15"],
            "uptime_seconds": 123,
            "cpu_count": 8,
            "memory_total_bytes": 17179869184,
            "health_status": "healthy",
        },
    )

    assert response.status_code == 200
    device = db.get(Device, UUID(enroll["device_id"]))
    assert device is not None
    assert device.hostname == "WIN-01-RENAMED"
    assert device.ip_address == "10.0.0.15"
    assert device.agent_version == "0.2.1"
    assert device.is_online is True

    checkin = db.scalar(select(DeviceCheckin).where(DeviceCheckin.device_id == device.id))
    assert checkin is not None
    assert checkin.payload["cpu_count"] == 8
    assert db.scalar(select(AuditLog).where(AuditLog.action == "agent.checkin")) is not None


def inventory_payload() -> dict[str, object]:
    return {
        "os_version": "11 Pro",
        "os_build": "22631",
        "cpu_model": "Intel Core Test",
        "cpu_cores": 8,
        "memory_total_bytes": 17179869184,
        "bios_vendor": "Contoso BIOS",
        "bios_version": "1.2.3",
        "system_manufacturer": "Contoso",
        "system_model": "Workstation",
        "disks": [
            {
                "name": "C:",
                "filesystem": "NTFS",
                "size_bytes": 512000000000,
                "free_bytes": 128000000000,
            }
        ],
        "network_interfaces": [
            {"name": "Ethernet", "mac_address": "00:11:22:33:44:55", "ip_addresses": ["10.0.0.15"]}
        ],
        "installed_software": [
            {"name": "Example App", "version": "1.0.0", "publisher": "Example Corp"}
        ],
        "security": {
            "antivirus_product": "Microsoft Defender",
            "antivirus_enabled": True,
            "antivirus_up_to_date": True,
            "defender_enabled": True,
            "firewall_enabled": True,
            "details": {"source": "test"},
        },
        "updates": {
            "pending_reboot": False,
            "update_status": "up_to_date",
            "details": {"source": "test"},
        },
    }


def test_inventory_checkin_upserts_latest_inventory_and_retrieval_endpoints(
    client: TestClient, db: Session
) -> None:
    org = create_org(db)
    client.headers.update(auth_headers(db, org))
    create_enrollment_token(db, org)
    enroll = client.post("/api/agent/enroll", json=enroll_payload()).json()

    response = client.post(
        "/api/agent/checkin",
        json={
            "device_id": enroll["device_id"],
            "device_secret": enroll["device_secret"],
            "hostname": "WIN-INV-01",
            "operating_system": "Windows",
            "architecture": "amd64",
            "agent_version": "0.3.0",
            "ip_address": "10.0.0.15",
            "local_ips": ["10.0.0.15"],
            "uptime_seconds": 500,
            "cpu_count": 8,
            "memory_total_bytes": 17179869184,
            "health_status": "healthy",
            "inventory": inventory_payload(),
        },
    )

    assert response.status_code == 200
    inventory = client.get(f"/api/devices/{enroll['device_id']}/inventory")
    assert inventory.status_code == 200
    inventory_body = inventory.json()
    assert inventory_body["cpu_model"] == "Intel Core Test"
    assert inventory_body["disks"][0]["filesystem"] == "NTFS"
    assert inventory_body["network_interfaces"][0]["mac_address"] == "00:11:22:33:44:55"

    software = client.get(f"/api/devices/{enroll['device_id']}/software")
    assert software.status_code == 200
    assert software.json()["software"][0]["name"] == "Example App"

    security = client.get(f"/api/devices/{enroll['device_id']}/security")
    assert security.status_code == 200
    assert security.json()["defender_enabled"] is True

    updates = client.get(f"/api/devices/{enroll['device_id']}/updates")
    assert updates.status_code == 200
    assert updates.json()["pending_reboot"] is False

    checkin = db.scalar(
        select(DeviceCheckin).where(DeviceCheckin.device_id == UUID(enroll["device_id"]))
    )
    assert checkin is not None
    assert "installed_software" not in checkin.payload
    assert checkin.payload["inventory_refreshed"] is True
    assert (
        db.scalar(
            select(DeviceInventory).where(DeviceInventory.device_id == UUID(enroll["device_id"]))
        )
        is not None
    )
    assert (
        db.scalar(select(InstalledSoftware).where(InstalledSoftware.name == "Example App"))
        is not None
    )
    assert db.scalar(select(AuditLog).where(AuditLog.action == "inventory.updated")) is not None


def alert_inventory_payload(
    *, low_disk: bool = True, defender_enabled: bool = False
) -> dict[str, object]:
    payload = inventory_payload()
    payload["disks"] = [
        {
            "name": "C:",
            "filesystem": "NTFS",
            "size_bytes": 1000000000,
            "free_bytes": 50000000 if low_disk else 500000000,
        }
    ]
    payload["security"] = {
        "antivirus_product": "Microsoft Defender",
        "antivirus_enabled": defender_enabled,
        "antivirus_up_to_date": True,
        "defender_enabled": defender_enabled,
        "firewall_enabled": True,
        "details": {"source": "test"},
    }
    payload["updates"] = {
        "pending_reboot": False,
        "update_status": "up_to_date",
        "details": {"source": "test"},
    }
    return payload


def post_inventory_checkin(
    client: TestClient,
    enroll: dict,
    *,
    low_disk: bool = True,
    defender_enabled: bool = False,
) -> None:
    response = client.post(
        "/api/agent/checkin",
        json={
            "device_id": enroll["device_id"],
            "device_secret": enroll["device_secret"],
            "hostname": "WIN-ALERT-01",
            "operating_system": "Windows",
            "architecture": "amd64",
            "agent_version": "0.3.0",
            "ip_address": "10.0.0.20",
            "local_ips": ["10.0.0.20"],
            "uptime_seconds": 500,
            "cpu_count": 8,
            "memory_total_bytes": 1000,
            "memory_used_bytes": 100,
            "health_status": "healthy",
            "inventory": alert_inventory_payload(
                low_disk=low_disk, defender_enabled=defender_enabled
            ),
        },
    )
    assert response.status_code == 200


def test_default_rule_evaluation_creates_expected_alerts(client: TestClient, db: Session) -> None:
    org = create_org(db)
    client.headers.update(auth_headers(db, org))
    create_enrollment_token(db, org)
    enroll = client.post("/api/agent/enroll", json=enroll_payload()).json()

    post_inventory_checkin(client, enroll, low_disk=True, defender_enabled=False)

    alerts = client.get("/api/alerts?status=active")
    assert alerts.status_code == 200
    alert_keys = {alert["rule_key"] for alert in alerts.json()}
    assert "low_disk_free_space" in alert_keys
    assert "defender_disabled" in alert_keys
    summary = client.get("/api/dashboard/summary")
    assert summary.status_code == 200
    assert summary.json()["active_warning_alerts"] >= 1
    assert summary.json()["active_critical_alerts"] >= 1


def test_duplicate_alert_prevention_records_repeated_event(client: TestClient, db: Session) -> None:
    org = create_org(db)
    client.headers.update(auth_headers(db, org))
    create_enrollment_token(db, org)
    enroll = client.post("/api/agent/enroll", json=enroll_payload()).json()

    post_inventory_checkin(client, enroll, low_disk=True, defender_enabled=True)
    post_inventory_checkin(client, enroll, low_disk=True, defender_enabled=True)

    alerts = client.get("/api/alerts?status=active").json()
    low_disk_alerts = [alert for alert in alerts if alert["rule_key"] == "low_disk_free_space"]
    assert len(low_disk_alerts) == 1
    detail = client.get(f"/api/alerts/{low_disk_alerts[0]['id']}").json()
    assert [event["event_type"] for event in detail["events"]].count("repeated") == 1


def test_alert_auto_resolution_when_condition_clears(client: TestClient, db: Session) -> None:
    org = create_org(db)
    client.headers.update(auth_headers(db, org))
    create_enrollment_token(db, org)
    enroll = client.post("/api/agent/enroll", json=enroll_payload()).json()

    post_inventory_checkin(client, enroll, low_disk=True, defender_enabled=True)
    active_alert = [
        alert
        for alert in client.get("/api/alerts?status=active").json()
        if alert["rule_key"] == "low_disk_free_space"
    ][0]
    post_inventory_checkin(client, enroll, low_disk=False, defender_enabled=True)

    resolved = client.get(f"/api/alerts/{active_alert['id']}").json()
    assert resolved["status"] == "resolved"
    assert "resolved" in [event["event_type"] for event in resolved["events"]]


def test_acknowledge_and_resolve_alert_endpoints(client: TestClient, db: Session) -> None:
    org = create_org(db)
    client.headers.update(auth_headers(db, org))
    create_enrollment_token(db, org)
    enroll = client.post("/api/agent/enroll", json=enroll_payload()).json()
    post_inventory_checkin(client, enroll, low_disk=True, defender_enabled=True)
    alert = [
        alert
        for alert in client.get("/api/alerts?status=active").json()
        if alert["rule_key"] == "low_disk_free_space"
    ][0]

    acknowledged = client.post(f"/api/alerts/{alert['id']}/acknowledge")
    assert acknowledged.status_code == 200
    assert acknowledged.json()["status"] == "acknowledged"

    device_alerts = client.get(f"/api/devices/{enroll['device_id']}/alerts")
    assert device_alerts.status_code == 200
    assert any(item["id"] == alert["id"] for item in device_alerts.json())

    resolved = client.post(f"/api/alerts/{alert['id']}/resolve")
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"


def test_job_creation_poll_start_complete_and_events(client: TestClient, db: Session) -> None:
    org = create_org(db)
    client.headers.update(auth_headers(db, org))
    create_enrollment_token(db, org)
    enroll = client.post("/api/agent/enroll", json=enroll_payload()).json()

    created = client.post(f"/api/devices/{enroll['device_id']}/jobs", json={"job_type": "ping"})
    assert created.status_code == 201
    job_id = created.json()["id"]

    polled = client.get(
        "/api/agent/jobs",
        params={"device_id": enroll["device_id"], "device_secret": enroll["device_secret"]},
    )
    assert polled.status_code == 200
    assert polled.json()[0]["id"] == job_id
    assert polled.json()[0]["status"] == "assigned"

    started = client.post(
        f"/api/agent/jobs/{job_id}/start",
        json={"device_id": enroll["device_id"], "device_secret": enroll["device_secret"]},
    )
    assert started.status_code == 200
    assert started.json()["status"] == "running"

    completed = client.post(
        f"/api/agent/jobs/{job_id}/complete",
        json={
            "device_id": enroll["device_id"],
            "device_secret": enroll["device_secret"],
            "succeeded": True,
            "output": "pong",
            "exit_code": 0,
            "metadata": {"handler": "ping"},
        },
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "succeeded"
    detail = client.get(f"/api/jobs/{job_id}").json()
    assert detail["result"]["output"] == "pong"
    assert {event["event_type"] for event in detail["events"]} >= {
        "created",
        "assigned",
        "started",
        "completed",
    }


def test_invalid_job_type_rejected(client: TestClient, db: Session) -> None:
    org = create_org(db)
    client.headers.update(auth_headers(db, org))
    create_enrollment_token(db, org)
    enroll = client.post("/api/agent/enroll", json=enroll_payload()).json()

    response = client.post(
        f"/api/devices/{enroll['device_id']}/jobs",
        json={"job_type": "run_shell", "payload": {"command": "whoami"}},
    )

    assert response.status_code == 400


def test_job_cancel_and_expiration(client: TestClient, db: Session) -> None:
    org = create_org(db)
    client.headers.update(auth_headers(db, org))
    create_enrollment_token(db, org)
    enroll = client.post("/api/agent/enroll", json=enroll_payload()).json()
    created = client.post(
        f"/api/devices/{enroll['device_id']}/jobs", json={"job_type": "collect_agent_logs"}
    ).json()

    canceled = client.post(f"/api/jobs/{created['id']}/cancel")
    assert canceled.status_code == 200
    assert canceled.json()["status"] == "canceled"

    expiring = client.post(
        f"/api/devices/{enroll['device_id']}/jobs", json={"job_type": "ping"}
    ).json()
    from datetime import UTC, datetime, timedelta

    from app.models.agent_job import AgentJob

    job = db.get(AgentJob, UUID(expiring["id"]))
    assert job is not None
    job.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()
    detail = client.get(f"/api/jobs/{expiring['id']}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "expired"


def test_agent_cannot_poll_or_update_other_device_jobs(client: TestClient, db: Session) -> None:
    org = create_org(db)
    client.headers.update(auth_headers(db, org))
    create_enrollment_token(db, org, token="enroll-token-value-abcdef", max_uses=2)
    first = client.post(
        "/api/agent/enroll", json=enroll_payload("enroll-token-value-abcdef")
    ).json()
    second_payload = enroll_payload("enroll-token-value-abcdef")
    second_payload["machine_identifier"] = "machine-guid-002"
    second_payload["hostname"] = "WIN-02"
    second = client.post("/api/agent/enroll", json=second_payload).json()
    job = client.post(f"/api/devices/{second['device_id']}/jobs", json={"job_type": "ping"}).json()

    wrong_poll = client.get(
        "/api/agent/jobs",
        params={"device_id": second["device_id"], "device_secret": first["device_secret"]},
    )
    assert wrong_poll.status_code == 401

    start = client.post(
        f"/api/agent/jobs/{job['id']}/start",
        json={"device_id": first["device_id"], "device_secret": first["device_secret"]},
    )
    assert start.status_code in {403, 409}


def test_notification_rule_matching_enqueues_delivery_on_new_alert(
    client: TestClient, db: Session
) -> None:
    org = create_org(db)
    client.headers.update(auth_headers(db, org))
    create_enrollment_token(db, org)
    channel = client.post(
        "/api/notification-channels",
        json={
            "organization_id": str(org.id),
            "name": "Ops Webhook",
            "channel_type": "webhook",
            "config": {
                "url": "https://hooks.example.test/alerts",
                "headers": {"Authorization": "Bearer secret"},
            },
        },
    )
    assert channel.status_code == 201
    rule = client.post(
        "/api/notification-rules",
        json={
            "organization_id": str(org.id),
            "name": "Critical low disk",
            "severity_filter": ["warning"],
            "alert_rule_type_filter": ["low_disk_free_space"],
            "channel_ids": [channel.json()["id"]],
        },
    )
    assert rule.status_code == 201
    enroll = client.post("/api/agent/enroll", json=enroll_payload()).json()

    post_inventory_checkin(client, enroll, low_disk=True, defender_enabled=True)

    deliveries = client.get("/api/notifications/deliveries")
    assert deliveries.status_code == 200
    body = deliveries.json()
    assert len(body) == 1
    assert body[0]["status"] == "pending"
    assert body[0]["channel_type"] == "webhook"


def test_repeated_detection_does_not_duplicate_notification_delivery(
    client: TestClient, db: Session
) -> None:
    org = create_org(db)
    client.headers.update(auth_headers(db, org))
    create_enrollment_token(db, org)
    channel = client.post(
        "/api/notification-channels",
        json={
            "organization_id": str(org.id),
            "name": "Ops Email",
            "channel_type": "email",
            "config": {"recipients": ["ops@example.test"]},
        },
    ).json()
    client.post(
        "/api/notification-rules",
        json={
            "organization_id": str(org.id),
            "name": "Warnings",
            "severity_filter": ["warning"],
            "channel_ids": [channel["id"]],
        },
    )
    enroll = client.post("/api/agent/enroll", json=enroll_payload()).json()

    post_inventory_checkin(client, enroll, low_disk=True, defender_enabled=True)
    post_inventory_checkin(client, enroll, low_disk=True, defender_enabled=True)

    deliveries = client.get("/api/notifications/deliveries").json()
    assert len(deliveries) == 1


def test_webhook_payload_shape(client: TestClient, db: Session) -> None:
    from app.core.notifications import build_webhook_payload
    from app.models.alert import Alert

    org = create_org(db)
    client.headers.update(auth_headers(db, org))
    create_enrollment_token(db, org)
    enroll = client.post("/api/agent/enroll", json=enroll_payload()).json()
    post_inventory_checkin(client, enroll, low_disk=True, defender_enabled=True)
    alert = db.scalar(select(Alert).where(Alert.severity == "warning"))
    assert alert is not None

    payload = build_webhook_payload(alert)

    assert payload["event"] == "alert.created"
    assert payload["alert"]["id"] == str(alert.id)
    assert payload["alert"]["severity"] == "warning"
    assert payload["alert"]["title"]


def test_notification_channel_masks_secret_headers(client: TestClient, db: Session) -> None:
    org = create_org(db)
    client.headers.update(auth_headers(db, org))
    response = client.post(
        "/api/notification-channels",
        json={
            "organization_id": str(org.id),
            "name": "Secret webhook",
            "channel_type": "webhook",
            "config": {
                "url": "https://hooks.example.test/alerts",
                "headers": {"Authorization": "Bearer secret", "X-Trace": "safe-value"},
            },
        },
    )

    assert response.status_code == 201
    config = response.json()["config"]
    assert config["headers"]["Authorization"] == "********"
    assert config["headers"]["X-Trace"] == "********"
    listed = client.get("/api/notification-channels").json()[0]
    assert listed["config"]["headers"]["Authorization"] == "********"


def test_login_success_failure_and_password_hashing(client: TestClient, db: Session) -> None:
    org = create_org(db)
    user = User(
        organization_id=org.id,
        email="login@example.test",
        hashed_password=hash_password("CorrectHorseBatteryStaple!1"),
        role="viewer",
        is_active=True,
    )
    db.add(user)
    db.commit()

    success = client.post(
        "/api/auth/login",
        json={"email": "login@example.test", "password": "CorrectHorseBatteryStaple!1"},
    )
    failure = client.post(
        "/api/auth/login",
        json={"email": "login@example.test", "password": "wrong-password"},
    )

    assert success.status_code == 200
    assert success.json()["access_token"]
    assert success.json()["refresh_token"]
    assert user.hashed_password != "CorrectHorseBatteryStaple!1"
    assert "hashed_password" not in success.text
    assert failure.status_code == 401


def test_refresh_token_rotation_and_logout(client: TestClient, db: Session) -> None:
    org = create_org(db)
    headers = auth_headers(db, org, role="viewer", email="refresh@example.test")
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    login = client.post(
        "/api/auth/login",
        json={"email": "refresh@example.test", "password": "CorrectHorseBatteryStaple!1"},
    ).json()

    refreshed = client.post("/api/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != login["refresh_token"]
    reused = client.post("/api/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert reused.status_code == 401
    logout = client.post(
        "/api/auth/logout", json={"refresh_token": refreshed.json()["refresh_token"]}
    )
    assert logout.status_code == 200
    after_logout = client.post(
        "/api/auth/refresh", json={"refresh_token": refreshed.json()["refresh_token"]}
    )
    assert after_logout.status_code == 401


def test_role_permission_checks_for_jobs_and_notifications(client: TestClient, db: Session) -> None:
    org = create_org(db)
    create_enrollment_token(db, org)
    owner_headers = auth_headers(db, org, role="owner", email="owner-rbac@example.test")
    enroll = client.post("/api/agent/enroll", json=enroll_payload()).json()

    viewer_headers = auth_headers(db, org, role="viewer", email="viewer-rbac@example.test")
    technician_headers = auth_headers(
        db, org, role="technician", email="technician-rbac@example.test"
    )
    admin_headers = auth_headers(db, org, role="admin", email="admin-rbac@example.test")

    viewer_job = client.post(
        f"/api/devices/{enroll['device_id']}/jobs",
        json={"job_type": "ping"},
        headers=viewer_headers,
    )
    technician_job = client.post(
        f"/api/devices/{enroll['device_id']}/jobs",
        json={"job_type": "ping"},
        headers=technician_headers,
    )
    technician_channel = client.post(
        "/api/notification-channels",
        json={
            "organization_id": str(org.id),
            "name": "Tech Webhook",
            "channel_type": "webhook",
            "config": {"url": "https://hooks.example.test/alerts"},
        },
        headers=technician_headers,
    )
    admin_channel = client.post(
        "/api/notification-channels",
        json={
            "organization_id": str(org.id),
            "name": "Admin Webhook",
            "channel_type": "webhook",
            "config": {"url": "https://hooks.example.test/alerts"},
        },
        headers=admin_headers,
    )
    users_as_admin = client.get("/api/users", headers=admin_headers)
    users_as_owner = client.get("/api/users", headers=owner_headers)

    assert viewer_job.status_code == 403
    assert technician_job.status_code == 201
    assert technician_channel.status_code == 403
    assert admin_channel.status_code == 201
    assert users_as_admin.status_code == 403
    assert users_as_owner.status_code == 200


def test_cross_tenant_access_prevention(client: TestClient, db: Session) -> None:
    org_a = create_org(db)
    org_b = Organization(name="Other MSP", slug="other")
    db.add(org_b)
    db.commit()
    create_enrollment_token(db, org_a)
    headers_a = auth_headers(db, org_a, role="owner", email="owner-a@example.test")
    headers_b = auth_headers(db, org_b, role="owner", email="owner-b@example.test")
    enroll = client.post("/api/agent/enroll", json=enroll_payload()).json()

    same_tenant = client.get(f"/api/devices/{enroll['device_id']}", headers=headers_a)
    other_tenant = client.get(f"/api/devices/{enroll['device_id']}", headers=headers_b)
    cross_tenant_job = client.post(
        f"/api/devices/{enroll['device_id']}/jobs",
        json={"job_type": "ping"},
        headers=headers_b,
    )

    assert same_tenant.status_code == 200
    assert other_tenant.status_code == 404
    assert cross_tenant_job.status_code == 404


def test_owner_can_manage_users_without_exposing_password_hashes(
    client: TestClient, db: Session
) -> None:
    org = create_org(db)
    owner_headers = auth_headers(db, org, role="owner", email="owner-users@example.test")

    created = client.post(
        "/api/users",
        json={
            "email": "new-viewer@example.test",
            "password": "CorrectHorseBatteryStaple!2",
            "role": "viewer",
        },
        headers=owner_headers,
    )
    assert created.status_code == 201
    assert "hashed_password" not in created.text
    user_id = created.json()["id"]

    patched = client.patch(
        f"/api/users/{user_id}", json={"role": "technician"}, headers=owner_headers
    )
    disabled = client.post(f"/api/users/{user_id}/disable", headers=owner_headers)
    enabled = client.post(f"/api/users/{user_id}/enable", headers=owner_headers)

    assert patched.status_code == 200
    assert patched.json()["role"] == "technician"
    assert disabled.status_code == 200
    assert disabled.json()["is_active"] is False
    assert enabled.status_code == 200
    assert enabled.json()["is_active"] is True


def test_bootstrap_status_before_setup(client: TestClient) -> None:
    response = client.get("/api/bootstrap/status")

    assert response.status_code == 200
    assert response.json() == {
        "has_organization": False,
        "has_owner": False,
        "setup_required": True,
    }


def test_successful_first_setup_returns_auth_response(client: TestClient, db: Session) -> None:
    response = client.post(
        "/api/bootstrap/setup",
        json={
            "organization_name": "Fresh MSP",
            "owner_name": "First Owner",
            "owner_email": "first-owner@example.test",
            "owner_password": "CorrectHorseBatteryStaple!3",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["role"] == "owner"
    assert "hashed_password" not in response.text
    assert db.scalar(select(User).where(User.email == "first-owner@example.test")) is not None


def test_setup_blocked_after_first_owner_exists(client: TestClient, db: Session) -> None:
    org = create_org(db)
    auth_headers(db, org, role="owner", email="existing-owner@example.test")

    response = client.post(
        "/api/bootstrap/setup",
        json={
            "organization_name": "Blocked MSP",
            "owner_name": "Blocked Owner",
            "owner_email": "blocked@example.test",
            "owner_password": "CorrectHorseBatteryStaple!4",
        },
    )

    assert response.status_code == 409


def test_bootstrap_weak_password_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/bootstrap/setup",
        json={
            "organization_name": "Weak MSP",
            "owner_name": "Weak Owner",
            "owner_email": "weak@example.test",
            "owner_password": "weakpassword",
        },
    )

    assert response.status_code == 400


def test_production_insecure_secret_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import Settings

    monkeypatch.setenv("CYCLOPE_ENVIRONMENT", "production")
    monkeypatch.setenv("CYCLOPE_DATABASE_URL", "postgresql+psycopg://example")
    monkeypatch.setenv("CYCLOPE_REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setenv("CYCLOPE_CORS_ALLOWED_ORIGINS", "https://central.example.test")
    monkeypatch.setenv("CYCLOPE_JWT_SECRET", "change-me-in-production")

    with pytest.raises(ValueError):
        Settings()


def test_production_secure_settings_are_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import Settings

    monkeypatch.setenv("CYCLOPE_ENVIRONMENT", "production")
    monkeypatch.setenv(
        "CYCLOPE_DATABASE_URL",
        "postgresql+psycopg://cyclope:strong-db-password@db.internal:5432/cyclope",
    )
    monkeypatch.setenv("CYCLOPE_REDIS_URL", "redis://cache.internal:6379/0")
    monkeypatch.setenv("CYCLOPE_CORS_ALLOWED_ORIGINS", "https://central.acme.test")
    monkeypatch.setenv("CYCLOPE_JWT_SECRET", "A" * 40)
    monkeypatch.setenv("CYCLOPE_TOKEN_HASH_PEPPER", "B" * 40)

    settings = Settings()

    assert settings.jwt_secret_key == "A" * 40


def test_production_insecure_token_pepper_rejected_without_leaking_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import Settings

    secret_value = "super-secret-value-that-must-not-appear"
    monkeypatch.setenv("CYCLOPE_ENVIRONMENT", "production")
    monkeypatch.setenv(
        "CYCLOPE_DATABASE_URL",
        "postgresql+psycopg://cyclope:strong-db-password@db.internal:5432/cyclope",
    )
    monkeypatch.setenv("CYCLOPE_REDIS_URL", "redis://cache.internal:6379/0")
    monkeypatch.setenv("CYCLOPE_CORS_ALLOWED_ORIGINS", "https://central.acme.test")
    monkeypatch.setenv("CYCLOPE_JWT_SECRET", secret_value)
    monkeypatch.setenv("CYCLOPE_TOKEN_HASH_PEPPER", "change-me-token-pepper")

    with pytest.raises(ValueError) as exc_info:
        Settings()

    message = str(exc_info.value)
    assert "TOKEN_HASH_PEPPER" in message
    assert secret_value not in message
