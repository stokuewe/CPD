# Service Contracts — Canonical Editor (M2.1)

Note: Desktop PySide6 app; no HTTP API introduced. Contracts below define service interfaces and signals/slots expected by the GUI. Persistence conforms strictly to sqlite.sql and azure.sql; parameterized SQL only; explicit transactions for writes.

## CanonicalService (synchronous facade, executes on worker threads)

- list_psets() -> List[Pset]
- create_pset(name: str, description: Optional[str]) -> Pset | Error(ValidationError)
- update_pset(pset_id: int, name?: str, description?: str) -> Pset | Error(ValidationError, Conflict)
- delete_pset(pset_id: int) -> Ok | Error(ConflictInUse, NotFound)

- list_attributes(pset_id: int) -> List[Attribute]
- create_attribute(pset_id: int, name: str, datatype: Optional[str], unit_id: Optional[int], value_domain_id: Optional[int]) -> Attribute | Error(ValidationError, Conflict)
- update_attribute(attr_id: int, name?: str, datatype?: Optional[str], unit_id?: Optional[int], value_domain_id?: Optional[int]) -> Attribute | Error(ValidationError, Conflict)
- delete_attribute(attr_id: int) -> Ok | Error(ConflictInUse, NotFound)

- list_units() -> List[Unit]
- list_value_domains() -> List[ValueDomain]
- list_value_items(domain_id: int) -> List[ValueItem]
- create_value_item(domain_id: int, code: str, label?: str) -> ValueItem | Error(ValidationError, Conflict)
- rename_value_item(item_id: int, code?: str, label?: str) -> ValueItem | Error(ValidationError, Conflict)
- delete_value_item(item_id: int) -> Ok | Error(NotFound)

## Validation
- Pset.name unique (DB enforced) + normalized case-insensitive comparison in app
- Attribute.name unique within Pset (app-enforced)
- Datatype must be one of {text, integer, real, boolean, date, datetime} if provided
- ValueItem labels unique per domain (normalized case-insensitive)

## Error Taxonomy (subset)
- ValidationError {field, message}
- Conflict {reason: DuplicateName | InUse | ConstraintViolation}
- NotFound
- StorageError {backend: sqlite|mssql, message, code}

## GUI Signals (main-thread)
- psetsLoaded(psets)
- attributesLoaded(pset_id, attributes)
- psetCreated(pset)
- attributeCreated(pset_id, attribute)
- psetUpdated(pset)
- attributeUpdated(attr)
- psetDeleted(pset_id)
- attributeDeleted(attr_id)
- valueDomainItemsChanged(domain_id)
- errorOccurred(error)

## Threading
- All service calls run in QThread/QThreadPool; results emitted via signals. UI must remain responsive per performance budgets.

