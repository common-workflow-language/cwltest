from typing import Any, Generic, Literal, TypeVar, TypedDict, List

ST = TypeVar('ST')

class ArvadosAPIRequest(Generic[ST]):
    def execute(self, num_retries: int = 0) -> ST: ...

class ApiClientAuthorization(TypedDict, total=False):
    etag: str
    api_token: str
    created_by_ip_address: str
    last_used_by_ip_address: str
    last_used_at: str
    expires_at: str
    created_at: str
    scopes: List[str]
    uuid: str

class ApiClientAuthorizationList(TypedDict, total=False):
    kind: str
    etag: str
    items: list[ApiClientAuthorization]

class ApiClientAuthorizations:
    def create(self, *, body: dict[Literal['api_client_authorization'], ApiClientAuthorization], cluster_id: str | None = None, ensure_unique_name: bool = False, select: List[str] | None = None) -> ArvadosAPIRequest[ApiClientAuthorization]: ...
    def create_system_auth(self, *, scopes: List[str] = ['all']) -> ArvadosAPIRequest[ApiClientAuthorization]: ...
    def current(self) -> ArvadosAPIRequest[ApiClientAuthorization]: ...
    def delete(self, *, uuid: str) -> ArvadosAPIRequest[ApiClientAuthorization]: ...
    def get(self, *, uuid: str, select: List[str] | None = None) -> ArvadosAPIRequest[ApiClientAuthorization]: ...
    def list(self, *, bypass_federation: bool = False, cluster_id: str | None = None, count: str = 'exact', distinct: bool = False, filters: List[str] | None = None, limit: int = 100, offset: int = 0, order: List[str] | None = None, select: List[str] | None = None, where: dict[str, Any] | None = None) -> ArvadosAPIRequest[ApiClientAuthorizationList]: ...
    def update(self, *, body: dict[Literal['api_client_authorization'], ApiClientAuthorization], uuid: str, select: List[str] | None = None) -> ArvadosAPIRequest[ApiClientAuthorization]: ...

class AuthorizedKey(TypedDict, total=False):
    etag: str
    uuid: str
    owner_uuid: str
    modified_by_user_uuid: str
    modified_at: str
    name: str
    key_type: str
    authorized_user_uuid: str
    public_key: str
    expires_at: str
    created_at: str

class AuthorizedKeyList(TypedDict, total=False):
    kind: str
    etag: str
    items: list[AuthorizedKey]

class AuthorizedKeys:
    def create(self, *, body: dict[Literal['authorized_key'], AuthorizedKey], cluster_id: str | None = None, ensure_unique_name: bool = False, select: List[str] | None = None) -> ArvadosAPIRequest[AuthorizedKey]: ...
    def delete(self, *, uuid: str) -> ArvadosAPIRequest[AuthorizedKey]: ...
    def get(self, *, uuid: str, select: List[str] | None = None) -> ArvadosAPIRequest[AuthorizedKey]: ...
    def list(self, *, bypass_federation: bool = False, cluster_id: str | None = None, count: str = 'exact', distinct: bool = False, filters: List[str] | None = None, limit: int = 100, offset: int = 0, order: List[str] | None = None, select: List[str] | None = None, where: dict[str, Any] | None = None) -> ArvadosAPIRequest[AuthorizedKeyList]: ...
    def update(self, *, body: dict[Literal['authorized_key'], AuthorizedKey], uuid: str, select: List[str] | None = None) -> ArvadosAPIRequest[AuthorizedKey]: ...

class Collection(TypedDict, total=False):
    etag: str
    owner_uuid: str
    created_at: str
    modified_by_user_uuid: str
    modified_at: str
    portable_data_hash: str
    replication_desired: int
    replication_confirmed_at: str
    replication_confirmed: int
    uuid: str
    manifest_text: str
    name: str
    description: str
    properties: dict[str, Any]
    delete_at: str
    trash_at: str
    is_trashed: bool
    storage_classes_desired: list[str]
    storage_classes_confirmed: list[str]
    storage_classes_confirmed_at: str
    current_version_uuid: str
    version: int
    preserve_version: bool
    file_count: int
    file_size_total: int

class CollectionList(TypedDict, total=False):
    kind: str
    etag: str
    items: list[Collection]

class Collections:
    def create(self, *, body: dict[Literal['collection'], Collection], cluster_id: str | None = None, ensure_unique_name: bool = False, replace_files: dict[str, Any] | None = None, select: List[str] | None = None) -> ArvadosAPIRequest[Collection]: ...
    def delete(self, *, uuid: str) -> ArvadosAPIRequest[Collection]: ...
    def get(self, *, uuid: str, include_trash: bool = False, select: List[str] | None = None) -> ArvadosAPIRequest[Collection]: ...
    def list(self, *, bypass_federation: bool = False, cluster_id: str | None = None, count: str = 'exact', distinct: bool = False, filters: List[str] | None = None, include_old_versions: bool = False, include_trash: bool = False, limit: int = 100, offset: int = 0, order: List[str] | None = None, select: List[str] | None = None, where: dict[str, Any] | None = None) -> ArvadosAPIRequest[CollectionList]: ...
    def provenance(self, *, uuid: str) -> ArvadosAPIRequest[Collection]: ...
    def trash(self, *, uuid: str) -> ArvadosAPIRequest[Collection]: ...
    def untrash(self, *, uuid: str) -> ArvadosAPIRequest[Collection]: ...
    def update(self, *, body: dict[Literal['collection'], Collection], uuid: str, replace_files: dict[str, Any] | None = None, select: List[str] | None = None) -> ArvadosAPIRequest[Collection]: ...
    def used_by(self, *, uuid: str) -> ArvadosAPIRequest[Collection]: ...

class ComputedPermission(TypedDict, total=False):
    user_uuid: str
    target_uuid: str
    perm_level: str

class ComputedPermissionList(TypedDict, total=False):
    kind: str
    etag: str
    items: list[ComputedPermission]

class ComputedPermissions:
    def list(self, *, count: str = 'exact', distinct: bool = False, filters: List[str] | None = None, limit: int = 100, order: List[str] | None = None, select: List[str] | None = None, where: dict[str, Any] | None = None) -> ArvadosAPIRequest[ComputedPermissionList]: ...

class Configs:
    def get(self) -> ArvadosAPIRequest[dict[str, Any]]: ...

class ContainerRequest(TypedDict, total=False):
    etag: str
    uuid: str
    owner_uuid: str
    created_at: str
    modified_at: str
    modified_by_user_uuid: str
    name: str
    description: str
    properties: dict[str, Any]
    state: str
    requesting_container_uuid: str
    container_uuid: str
    container_count_max: int
    mounts: dict[str, Any]
    runtime_constraints: dict[str, Any]
    container_image: str
    environment: dict[str, Any]
    cwd: str
    command: list[str]
    output_path: str
    priority: int
    expires_at: str
    filters: str
    container_count: int
    use_existing: bool
    scheduling_parameters: dict[str, Any]
    output_uuid: str
    log_uuid: str
    output_name: str
    output_ttl: int
    output_storage_classes: list[str]
    output_properties: dict[str, Any]
    cumulative_cost: float
    output_glob: list[str]

class ContainerRequestList(TypedDict, total=False):
    kind: str
    etag: str
    items: list[ContainerRequest]

class ContainerRequests:
    def container_status(self, *, uuid: str) -> ArvadosAPIRequest[ContainerRequest]: ...
    def create(self, *, body: dict[Literal['container_request'], ContainerRequest], cluster_id: str | None = None, ensure_unique_name: bool = False, select: List[str] | None = None) -> ArvadosAPIRequest[ContainerRequest]: ...
    def delete(self, *, uuid: str) -> ArvadosAPIRequest[ContainerRequest]: ...
    def get(self, *, uuid: str, include_trash: bool = False, select: List[str] | None = None) -> ArvadosAPIRequest[ContainerRequest]: ...
    def list(self, *, bypass_federation: bool = False, cluster_id: str | None = None, count: str = 'exact', distinct: bool = False, filters: List[str] | None = None, include_trash: bool = False, limit: int = 100, offset: int = 0, order: List[str] | None = None, select: List[str] | None = None, where: dict[str, Any] | None = None) -> ArvadosAPIRequest[ContainerRequestList]: ...
    def update(self, *, body: dict[Literal['container_request'], ContainerRequest], uuid: str, select: List[str] | None = None) -> ArvadosAPIRequest[ContainerRequest]: ...

class Container(TypedDict, total=False):
    etag: str
    uuid: str
    owner_uuid: str
    created_at: str
    modified_at: str
    modified_by_user_uuid: str
    state: str
    started_at: str
    finished_at: str
    log: str
    environment: dict[str, Any]
    cwd: str
    command: list[str]
    output_path: str
    mounts: dict[str, Any]
    runtime_constraints: dict[str, Any]
    output: str
    container_image: str
    progress: float
    priority: int
    exit_code: int
    auth_uuid: str
    locked_by_uuid: str
    scheduling_parameters: dict[str, Any]
    runtime_status: dict[str, Any]
    runtime_user_uuid: str
    runtime_auth_scopes: list[str]
    lock_count: int
    gateway_address: str
    interactive_session_started: bool
    output_storage_classes: list[str]
    output_properties: dict[str, Any]
    cost: float
    subrequests_cost: float
    output_glob: list[str]

class ContainerList(TypedDict, total=False):
    kind: str
    etag: str
    items: list[Container]

class Containers:
    def auth(self, *, uuid: str) -> ArvadosAPIRequest[Container]: ...
    def create(self, *, body: dict[Literal['container'], Container], cluster_id: str | None = None, ensure_unique_name: bool = False, select: List[str] | None = None) -> ArvadosAPIRequest[Container]: ...
    def current(self) -> ArvadosAPIRequest[Container]: ...
    def delete(self, *, uuid: str) -> ArvadosAPIRequest[Container]: ...
    def get(self, *, uuid: str, select: List[str] | None = None) -> ArvadosAPIRequest[Container]: ...
    def list(self, *, bypass_federation: bool = False, cluster_id: str | None = None, count: str = 'exact', distinct: bool = False, filters: List[str] | None = None, limit: int = 100, offset: int = 0, order: List[str] | None = None, select: List[str] | None = None, where: dict[str, Any] | None = None) -> ArvadosAPIRequest[ContainerList]: ...
    def lock(self, *, uuid: str) -> ArvadosAPIRequest[Container]: ...
    def secret_mounts(self, *, uuid: str) -> ArvadosAPIRequest[Container]: ...
    def unlock(self, *, uuid: str) -> ArvadosAPIRequest[Container]: ...
    def update(self, *, body: dict[Literal['container'], Container], uuid: str, select: List[str] | None = None) -> ArvadosAPIRequest[Container]: ...
    def update_priority(self, *, uuid: str) -> ArvadosAPIRequest[Container]: ...

class Group(TypedDict, total=False):
    etag: str
    uuid: str
    owner_uuid: str
    created_at: str
    modified_by_user_uuid: str
    modified_at: str
    name: str
    description: str
    group_class: str
    trash_at: str
    is_trashed: bool
    delete_at: str
    properties: dict[str, Any]
    frozen_by_uuid: str

class GroupList(TypedDict, total=False):
    kind: str
    etag: str
    items: list[Group]

class Groups:
    def contents(self, *, bypass_federation: bool = False, cluster_id: str | None = None, count: str = 'exact', distinct: bool = False, exclude_home_project: bool = False, filters: List[str] | None = None, include: List[str] | None = None, include_old_versions: bool = False, include_trash: bool = False, limit: int = 100, offset: int = 0, order: List[str] | None = None, recursive: bool = False, select: List[str] | None = None, uuid: str = '', where: dict[str, Any] | None = None) -> ArvadosAPIRequest[Group]: ...
    def create(self, *, body: dict[Literal['group'], Group], async_: bool = False, cluster_id: str | None = None, ensure_unique_name: bool = False, select: List[str] | None = None) -> ArvadosAPIRequest[Group]: ...
    def delete(self, *, uuid: str) -> ArvadosAPIRequest[Group]: ...
    def get(self, *, uuid: str, include_trash: bool = False, select: List[str] | None = None) -> ArvadosAPIRequest[Group]: ...
    def list(self, *, bypass_federation: bool = False, cluster_id: str | None = None, count: str = 'exact', distinct: bool = False, filters: List[str] | None = None, include_trash: bool = False, limit: int = 100, offset: int = 0, order: List[str] | None = None, select: List[str] | None = None, where: dict[str, Any] | None = None) -> ArvadosAPIRequest[GroupList]: ...
    def shared(self, *, bypass_federation: bool = False, cluster_id: str | None = None, count: str = 'exact', distinct: bool = False, filters: List[str] | None = None, include: str | None = None, include_trash: bool = False, limit: int = 100, offset: int = 0, order: List[str] | None = None, select: List[str] | None = None, where: dict[str, Any] | None = None) -> ArvadosAPIRequest[Group]: ...
    def trash(self, *, uuid: str) -> ArvadosAPIRequest[Group]: ...
    def untrash(self, *, uuid: str) -> ArvadosAPIRequest[Group]: ...
    def update(self, *, body: dict[Literal['group'], Group], uuid: str, async_: bool = False, select: List[str] | None = None) -> ArvadosAPIRequest[Group]: ...

class KeepService(TypedDict, total=False):
    etag: str
    uuid: str
    owner_uuid: str
    modified_by_user_uuid: str
    modified_at: str
    service_host: str
    service_port: int
    service_ssl_flag: bool
    service_type: str
    created_at: str
    read_only: bool

class KeepServiceList(TypedDict, total=False):
    kind: str
    etag: str
    items: list[KeepService]

class KeepServices:
    def accessible(self) -> ArvadosAPIRequest[KeepService]: ...
    def create(self, *, body: dict[Literal['keep_service'], KeepService], cluster_id: str | None = None, ensure_unique_name: bool = False, select: List[str] | None = None) -> ArvadosAPIRequest[KeepService]: ...
    def delete(self, *, uuid: str) -> ArvadosAPIRequest[KeepService]: ...
    def get(self, *, uuid: str, select: List[str] | None = None) -> ArvadosAPIRequest[KeepService]: ...
    def list(self, *, bypass_federation: bool = False, cluster_id: str | None = None, count: str = 'exact', distinct: bool = False, filters: List[str] | None = None, limit: int = 100, offset: int = 0, order: List[str] | None = None, select: List[str] | None = None, where: dict[str, Any] | None = None) -> ArvadosAPIRequest[KeepServiceList]: ...
    def update(self, *, body: dict[Literal['keep_service'], KeepService], uuid: str, select: List[str] | None = None) -> ArvadosAPIRequest[KeepService]: ...

class Link(TypedDict, total=False):
    etag: str
    uuid: str
    owner_uuid: str
    created_at: str
    modified_by_user_uuid: str
    modified_at: str
    tail_uuid: str
    link_class: str
    name: str
    head_uuid: str
    properties: dict[str, Any]

class LinkList(TypedDict, total=False):
    kind: str
    etag: str
    items: list[Link]

class Links:
    def create(self, *, body: dict[Literal['link'], Link], cluster_id: str | None = None, ensure_unique_name: bool = False, select: List[str] | None = None) -> ArvadosAPIRequest[Link]: ...
    def delete(self, *, uuid: str) -> ArvadosAPIRequest[Link]: ...
    def get(self, *, uuid: str, select: List[str] | None = None) -> ArvadosAPIRequest[Link]: ...
    def get_permissions(self, *, uuid: str) -> ArvadosAPIRequest[Link]: ...
    def list(self, *, bypass_federation: bool = False, cluster_id: str | None = None, count: str = 'exact', distinct: bool = False, filters: List[str] | None = None, limit: int = 100, offset: int = 0, order: List[str] | None = None, select: List[str] | None = None, where: dict[str, Any] | None = None) -> ArvadosAPIRequest[LinkList]: ...
    def update(self, *, body: dict[Literal['link'], Link], uuid: str, select: List[str] | None = None) -> ArvadosAPIRequest[Link]: ...

class Log(TypedDict, total=False):
    etag: str
    id: int
    uuid: str
    owner_uuid: str
    modified_by_user_uuid: str
    object_uuid: str
    event_at: str
    event_type: str
    summary: str
    properties: dict[str, Any]
    created_at: str
    modified_at: str
    object_owner_uuid: str

class LogList(TypedDict, total=False):
    kind: str
    etag: str
    items: list[Log]

class Logs:
    def create(self, *, body: dict[Literal['log'], Log], cluster_id: str | None = None, ensure_unique_name: bool = False, select: List[str] | None = None) -> ArvadosAPIRequest[Log]: ...
    def delete(self, *, uuid: str) -> ArvadosAPIRequest[Log]: ...
    def get(self, *, uuid: str, select: List[str] | None = None) -> ArvadosAPIRequest[Log]: ...
    def list(self, *, bypass_federation: bool = False, cluster_id: str | None = None, count: str = 'exact', distinct: bool = False, filters: List[str] | None = None, limit: int = 100, offset: int = 0, order: List[str] | None = None, select: List[str] | None = None, where: dict[str, Any] | None = None) -> ArvadosAPIRequest[LogList]: ...
    def update(self, *, body: dict[Literal['log'], Log], uuid: str, select: List[str] | None = None) -> ArvadosAPIRequest[Log]: ...

class Sys:
    def get(self) -> ArvadosAPIRequest[dict[str, Any]]: ...

class UserAgreement(TypedDict, total=False):
    etag: str
    owner_uuid: str
    created_at: str
    modified_by_user_uuid: str
    modified_at: str
    portable_data_hash: str
    replication_desired: int
    replication_confirmed_at: str
    replication_confirmed: int
    uuid: str
    manifest_text: str
    name: str
    description: str
    properties: dict[str, Any]
    delete_at: str
    trash_at: str
    is_trashed: bool
    storage_classes_desired: list[str]
    storage_classes_confirmed: list[str]
    storage_classes_confirmed_at: str
    current_version_uuid: str
    version: int
    preserve_version: bool
    file_count: int
    file_size_total: int

class UserAgreementList(TypedDict, total=False):
    kind: str
    etag: str
    items: list[UserAgreement]

class UserAgreements:
    def create(self, *, body: dict[Literal['user_agreement'], UserAgreement], cluster_id: str | None = None, ensure_unique_name: bool = False, select: List[str] | None = None) -> ArvadosAPIRequest[UserAgreement]: ...
    def delete(self, *, uuid: str) -> ArvadosAPIRequest[UserAgreement]: ...
    def get(self, *, uuid: str, select: List[str] | None = None) -> ArvadosAPIRequest[UserAgreement]: ...
    def list(self, *, bypass_federation: bool = False, cluster_id: str | None = None, count: str = 'exact', distinct: bool = False, filters: List[str] | None = None, limit: int = 100, offset: int = 0, order: List[str] | None = None, select: List[str] | None = None, where: dict[str, Any] | None = None) -> ArvadosAPIRequest[UserAgreementList]: ...
    def sign(self) -> ArvadosAPIRequest[UserAgreement]: ...
    def signatures(self) -> ArvadosAPIRequest[UserAgreement]: ...
    def update(self, *, body: dict[Literal['user_agreement'], UserAgreement], uuid: str, select: List[str] | None = None) -> ArvadosAPIRequest[UserAgreement]: ...

class User(TypedDict, total=False):
    etag: str
    uuid: str
    owner_uuid: str
    created_at: str
    modified_by_user_uuid: str
    modified_at: str
    email: str
    first_name: str
    last_name: str
    identity_url: str
    is_admin: bool
    prefs: dict[str, Any]
    is_active: bool
    username: str

class UserList(TypedDict, total=False):
    kind: str
    etag: str
    items: list[User]

class Users:
    def activate(self, *, uuid: str) -> ArvadosAPIRequest[User]: ...
    def create(self, *, body: dict[Literal['user'], User], cluster_id: str | None = None, ensure_unique_name: bool = False, select: List[str] | None = None) -> ArvadosAPIRequest[User]: ...
    def current(self) -> ArvadosAPIRequest[User]: ...
    def delete(self, *, uuid: str) -> ArvadosAPIRequest[User]: ...
    def get(self, *, uuid: str, select: List[str] | None = None) -> ArvadosAPIRequest[User]: ...
    def list(self, *, bypass_federation: bool = False, cluster_id: str | None = None, count: str = 'exact', distinct: bool = False, filters: List[str] | None = None, limit: int = 100, offset: int = 0, order: List[str] | None = None, select: List[str] | None = None, where: dict[str, Any] | None = None) -> ArvadosAPIRequest[UserList]: ...
    def merge(self, *, new_owner_uuid: str, new_user_token: str | None = None, new_user_uuid: str | None = None, old_user_uuid: str | None = None, redirect_to_new_user: bool = False) -> ArvadosAPIRequest[User]: ...
    def setup(self, *, repo_name: str | None = None, send_notification_email: bool = False, user: dict[str, Any] | None = None, uuid: str | None = None, vm_uuid: str | None = None) -> ArvadosAPIRequest[User]: ...
    def system(self) -> ArvadosAPIRequest[User]: ...
    def unsetup(self, *, uuid: str) -> ArvadosAPIRequest[User]: ...
    def update(self, *, body: dict[Literal['user'], User], uuid: str, bypass_federation: bool = False, select: List[str] | None = None) -> ArvadosAPIRequest[User]: ...

class VirtualMachine(TypedDict, total=False):
    etag: str
    uuid: str
    owner_uuid: str
    modified_by_user_uuid: str
    modified_at: str
    hostname: str
    created_at: str

class VirtualMachineList(TypedDict, total=False):
    kind: str
    etag: str
    items: list[VirtualMachine]

class VirtualMachines:
    def create(self, *, body: dict[Literal['virtual_machine'], VirtualMachine], cluster_id: str | None = None, ensure_unique_name: bool = False, select: List[str] | None = None) -> ArvadosAPIRequest[VirtualMachine]: ...
    def delete(self, *, uuid: str) -> ArvadosAPIRequest[VirtualMachine]: ...
    def get(self, *, uuid: str, select: List[str] | None = None) -> ArvadosAPIRequest[VirtualMachine]: ...
    def get_all_logins(self) -> ArvadosAPIRequest[VirtualMachine]: ...
    def list(self, *, bypass_federation: bool = False, cluster_id: str | None = None, count: str = 'exact', distinct: bool = False, filters: List[str] | None = None, limit: int = 100, offset: int = 0, order: List[str] | None = None, select: List[str] | None = None, where: dict[str, Any] | None = None) -> ArvadosAPIRequest[VirtualMachineList]: ...
    def logins(self, *, uuid: str) -> ArvadosAPIRequest[VirtualMachine]: ...
    def update(self, *, body: dict[Literal['virtual_machine'], VirtualMachine], uuid: str, select: List[str] | None = None) -> ArvadosAPIRequest[VirtualMachine]: ...

class Vocabularies:
    def get(self) -> ArvadosAPIRequest[dict[str, Any]]: ...

class Workflow(TypedDict, total=False):
    etag: str
    uuid: str
    owner_uuid: str
    created_at: str
    modified_at: str
    modified_by_user_uuid: str
    name: str
    description: str
    definition: str

class WorkflowList(TypedDict, total=False):
    kind: str
    etag: str
    items: list[Workflow]

class Workflows:
    def create(self, *, body: dict[Literal['workflow'], Workflow], cluster_id: str | None = None, ensure_unique_name: bool = False, select: List[str] | None = None) -> ArvadosAPIRequest[Workflow]: ...
    def delete(self, *, uuid: str) -> ArvadosAPIRequest[Workflow]: ...
    def get(self, *, uuid: str, select: List[str] | None = None) -> ArvadosAPIRequest[Workflow]: ...
    def list(self, *, bypass_federation: bool = False, cluster_id: str | None = None, count: str = 'exact', distinct: bool = False, filters: List[str] | None = None, limit: int = 100, offset: int = 0, order: List[str] | None = None, select: List[str] | None = None, where: dict[str, Any] | None = None) -> ArvadosAPIRequest[WorkflowList]: ...
    def update(self, *, body: dict[Literal['workflow'], Workflow], uuid: str, select: List[str] | None = None) -> ArvadosAPIRequest[Workflow]: ...

class ArvadosAPIClient:
    def api_client_authorizations(self) -> ApiClientAuthorizations: ...
    def authorized_keys(self) -> AuthorizedKeys: ...
    def collections(self) -> Collections: ...
    def computed_permissions(self) -> ComputedPermissions: ...
    def configs(self) -> Configs: ...
    def container_requests(self) -> ContainerRequests: ...
    def containers(self) -> Containers: ...
    def groups(self) -> Groups: ...
    def keep_services(self) -> KeepServices: ...
    def links(self) -> Links: ...
    def logs(self) -> Logs: ...
    def sys(self) -> Sys: ...
    def user_agreements(self) -> UserAgreements: ...
    def users(self) -> Users: ...
    def virtual_machines(self) -> VirtualMachines: ...
    def vocabularies(self) -> Vocabularies: ...
    def workflows(self) -> Workflows: ...
