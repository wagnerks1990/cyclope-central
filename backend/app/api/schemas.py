from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AgentEnrollRequest(BaseModel):
    enrollment_token: str = Field(min_length=16)
    hostname: str = Field(min_length=1, max_length=255)
    operating_system: str = Field(min_length=1, max_length=128)
    architecture: str = Field(min_length=1, max_length=64)
    agent_version: str = Field(min_length=1, max_length=64)
    machine_identifier: str = Field(min_length=1, max_length=255)


class AgentEnrollResponse(BaseModel):
    device_id: UUID
    device_secret: str


class DiskInventoryPayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    filesystem: str | None = Field(default=None, max_length=64)
    size_bytes: int | None = Field(default=None, ge=0)
    free_bytes: int | None = Field(default=None, ge=0)


class NetworkInterfaceInventoryPayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    mac_address: str | None = Field(default=None, max_length=64)
    ip_addresses: list[str] = Field(default_factory=list)


class InstalledSoftwarePayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    version: str | None = Field(default=None, max_length=128)
    publisher: str | None = Field(default=None, max_length=255)
    installed_at: datetime | None = None


class SecurityStatusPayload(BaseModel):
    antivirus_product: str | None = Field(default=None, max_length=255)
    antivirus_enabled: bool | None = None
    antivirus_up_to_date: bool | None = None
    defender_enabled: bool | None = None
    firewall_enabled: bool | None = None
    details: dict = Field(default_factory=dict)


class UpdateStatusPayload(BaseModel):
    pending_reboot: bool | None = None
    update_status: str | None = Field(default=None, max_length=128)
    last_update_check_at: datetime | None = None
    details: dict = Field(default_factory=dict)


class DeviceInventoryPayload(BaseModel):
    os_version: str | None = Field(default=None, max_length=128)
    os_build: str | None = Field(default=None, max_length=128)
    cpu_model: str | None = Field(default=None, max_length=255)
    cpu_cores: int | None = Field(default=None, ge=0)
    memory_total_bytes: int | None = Field(default=None, ge=0)
    bios_vendor: str | None = Field(default=None, max_length=255)
    bios_version: str | None = Field(default=None, max_length=255)
    system_manufacturer: str | None = Field(default=None, max_length=255)
    system_model: str | None = Field(default=None, max_length=255)
    disks: list[DiskInventoryPayload] = Field(default_factory=list, max_length=128)
    network_interfaces: list[NetworkInterfaceInventoryPayload] = Field(
        default_factory=list, max_length=128
    )
    installed_software: list[InstalledSoftwarePayload] = Field(
        default_factory=list, max_length=2048
    )
    security: SecurityStatusPayload | None = None
    updates: UpdateStatusPayload | None = None


class AgentCheckinRequest(BaseModel):
    device_id: UUID
    device_secret: str = Field(min_length=16)
    hostname: str = Field(min_length=1, max_length=255)
    operating_system: str = Field(min_length=1, max_length=128)
    architecture: str | None = Field(default=None, max_length=64)
    agent_version: str = Field(min_length=1, max_length=64)
    ip_address: str | None = Field(default=None, max_length=64)
    local_ips: list[str] = Field(default_factory=list)
    uptime_seconds: int | None = Field(default=None, ge=0)
    cpu_count: int | None = Field(default=None, ge=0)
    memory_total_bytes: int | None = Field(default=None, ge=0)
    memory_used_bytes: int | None = Field(default=None, ge=0)
    health_status: str = Field(default="healthy", max_length=64)
    inventory: DeviceInventoryPayload | None = None


class AgentCheckinResponse(BaseModel):
    status: str
    device_id: UUID
    checked_in_at: datetime


class CheckinSummary(BaseModel):
    checked_in_at: datetime
    status: str
    ip_address: str | None = None
    agent_version: str | None = None
    payload: dict


class DeviceSummary(BaseModel):
    id: UUID
    hostname: str
    operating_system: str
    architecture: str | None = None
    ip_address: str | None = None
    agent_version: str | None = None
    health_status: str
    status: str
    is_online: bool
    last_seen_at: datetime | None = None


class DeviceDetail(DeviceSummary):
    machine_identifier: str
    latest_checkin: CheckinSummary | None = None


class DiskInventoryResponse(DiskInventoryPayload):
    id: UUID


class NetworkInterfaceInventoryResponse(NetworkInterfaceInventoryPayload):
    id: UUID


class DeviceInventoryResponse(BaseModel):
    device_id: UUID
    hostname: str
    operating_system: str
    os_version: str | None = None
    os_build: str | None = None
    architecture: str | None = None
    agent_version: str | None = None
    cpu_model: str | None = None
    cpu_cores: int | None = None
    memory_total_bytes: int | None = None
    bios_vendor: str | None = None
    bios_version: str | None = None
    system_manufacturer: str | None = None
    system_model: str | None = None
    inventory_refreshed_at: datetime
    disks: list[DiskInventoryResponse] = Field(default_factory=list)
    network_interfaces: list[NetworkInterfaceInventoryResponse] = Field(default_factory=list)


class InstalledSoftwareResponse(InstalledSoftwarePayload):
    id: UUID


class SoftwareInventoryResponse(BaseModel):
    device_id: UUID
    inventory_refreshed_at: datetime | None = None
    software: list[InstalledSoftwareResponse] = Field(default_factory=list)


class SecurityStatusResponse(SecurityStatusPayload):
    device_id: UUID
    refreshed_at: datetime


class UpdateStatusResponse(UpdateStatusPayload):
    device_id: UUID
    refreshed_at: datetime


class AlertEventResponse(BaseModel):
    id: UUID
    event_type: str
    message: str
    metadata_json: dict
    created_at: datetime


class AlertResponse(BaseModel):
    id: UUID
    organization_id: UUID
    device_id: UUID
    rule_id: UUID
    severity: str
    status: str
    title: str
    message: str
    first_seen_at: datetime
    last_seen_at: datetime
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    device_hostname: str | None = None
    rule_key: str | None = None
    events: list[AlertEventResponse] = Field(default_factory=list)


class DashboardSummaryResponse(BaseModel):
    total_devices: int
    online_devices: int
    offline_devices: int
    active_warning_alerts: int
    active_critical_alerts: int
    devices_needing_attention: int
    recent_alerts: list[AlertResponse] = Field(default_factory=list)


class AgentJobCreateRequest(BaseModel):
    job_type: str = Field(min_length=1, max_length=64)
    payload: dict = Field(default_factory=dict)


class AgentJobEventResponse(BaseModel):
    id: UUID
    event_type: str
    message: str
    metadata_json: dict
    created_at: datetime


class AgentJobResultResponse(BaseModel):
    id: UUID
    status: str
    output: str
    error: str | None = None
    exit_code: int | None = None
    metadata_json: dict
    created_at: datetime


class AgentJobResponse(BaseModel):
    id: UUID
    organization_id: UUID
    device_id: UUID
    assigned_agent_id: UUID | None = None
    job_type: str
    status: str
    payload: dict
    expires_at: datetime
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result_summary: str | None = None
    result: AgentJobResultResponse | None = None
    events: list[AgentJobEventResponse] = Field(default_factory=list)


class AgentJobPollRequest(BaseModel):
    device_id: UUID
    device_secret: str = Field(min_length=16)


class AgentJobCompleteRequest(AgentJobPollRequest):
    succeeded: bool
    output: str = Field(default="", max_length=20000)
    error: str | None = Field(default=None, max_length=20000)
    exit_code: int | None = None
    metadata: dict = Field(default_factory=dict)


class NotificationChannelCreateRequest(BaseModel):
    organization_id: UUID
    name: str = Field(min_length=1, max_length=255)
    channel_type: str = Field(pattern="^(email|webhook)$")
    enabled: bool = True
    config: dict = Field(default_factory=dict)


class NotificationChannelPatchRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    enabled: bool | None = None
    config: dict | None = None


class NotificationChannelResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    channel_type: str
    enabled: bool
    config: dict
    created_at: datetime
    updated_at: datetime


class NotificationRuleCreateRequest(BaseModel):
    organization_id: UUID
    name: str = Field(min_length=1, max_length=255)
    enabled: bool = True
    severity_filter: list[str] = Field(default_factory=list)
    alert_rule_type_filter: list[str] = Field(default_factory=list)
    channel_ids: list[UUID] = Field(min_length=1)


class NotificationRulePatchRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    enabled: bool | None = None
    severity_filter: list[str] | None = None
    alert_rule_type_filter: list[str] | None = None
    channel_ids: list[UUID] | None = None


class NotificationRuleResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    enabled: bool
    severity_filter: list[str]
    alert_rule_type_filter: list[str]
    channel_ids: list[UUID]
    created_at: datetime
    updated_at: datetime


class NotificationDeliveryResponse(BaseModel):
    id: UUID
    organization_id: UUID
    alert_id: UUID
    channel_id: UUID
    channel_name: str | None = None
    channel_type: str | None = None
    status: str
    attempts: int
    last_error: str | None = None
    created_at: datetime
    sent_at: datetime | None = None
