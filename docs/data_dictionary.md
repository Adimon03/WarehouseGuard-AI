# Data Dictionary

## warehouses

| Column | Type | Description |
|--------|------|-------------|
| id | int PK | Primary key |
| name | str | Warehouse name |
| location | str | Geographic location |
| total_area_sqm | float | Total area in square metres |
| manager | str | Manager name |
| created_at | datetime | Creation timestamp |

## zones

| Column | Type | Description |
|--------|------|-------------|
| id | int PK | Primary key |
| warehouse_id | int FK→warehouses | Parent warehouse |
| name | str | Zone name |
| zone_type | str | ambient, cold_storage, frozen, hazardous |
| area_sqm | float | Zone area |
| max_occupancy | int | Max allowed occupancy |
| min_temp_c | float | Min allowed temperature |
| max_temp_c | float | Max allowed temperature |
| min_humidity_pct | float | Min allowed humidity |
| max_humidity_pct | float | Max allowed humidity |

## sensors

| Column | Type | Description |
|--------|------|-------------|
| id | int PK | Primary key |
| zone_id | int FK→zones | Assigned zone |
| sensor_type | str | temperature, humidity, occupancy, door |
| status | str | active, drift, offline |
| manufacturer | str | Manufacturer name |
| model | str | Sensor model |
| installed_at | datetime | Install date |
| last_calibrated_at | datetime | Last calibration date |

## sensor_zone_mappings

| Column | Type | Description |
|--------|------|-------------|
| id | int PK | Primary key |
| sensor_id | int FK→sensors | Sensor |
| zone_id | int FK→zones | Zone |
| is_primary | bool | Primary assignment |
| justification | str nullable | Reason for mapping (null = anomaly) |
| assigned_at | datetime | Assignment date |

## sensor_readings

| Column | Type | Description |
|--------|------|-------------|
| id | int PK | Primary key |
| sensor_id | int FK→sensors | Source sensor |
| reading_timestamp | datetime | Reading time |
| temperature_c | float nullable | Temperature value |
| humidity_pct | float nullable | Humidity value |
| occupancy_count | int nullable | Occupancy count |
| door_state | str nullable | open, closed |
| is_missing | bool | True = sensor outage |
| is_anomaly_injected | bool | Internal ground-truth flag (NOT used by detection) |

## door_events

| Column | Type | Description |
|--------|------|-------------|
| id | int PK | Primary key |
| zone_id | int FK→zones | Zone |
| sensor_id | int FK→sensors | Door sensor |
| event_timestamp | datetime | Event time |
| event_type | str | open, close |
| duration_seconds | float | Open duration |
| is_anomaly_injected | bool | Internal flag |

## storage_requirements

| Column | Type | Description |
|--------|------|-------------|
| id | int PK | Primary key |
| product_category | str unique | Product category |
| min_temp_c | float | Min storage temp |
| max_temp_c | float | Max storage temp |
| min_humidity_pct | float | Min storage humidity |
| max_humidity_pct | float | Max storage humidity |
| dwell_time_limit_days | int | Max dwell time |
| compatible_zone_types | JSON | Compatible zone types array |

## inventory_lots

| Column | Type | Description |
|--------|------|-------------|
| id | int PK | Primary key |
| zone_id | int FK→zones | Storage zone |
| product_name | str | Product name |
| product_category | str | Category |
| quantity | int | Quantity |
| unit | str | Unit of measure |
| batch_number | str | Batch ID |
| arrival_date | datetime | Arrival time |
| departure_date | datetime nullable | Departure time |
| status | str | stored, departed, expired |

## alarms

| Column | Type | Description |
|--------|------|-------------|
| id | int PK | Primary key |
| alarm_type | str | Type of anomaly |
| severity | str | critical, warning, info |
| zone_id | int FK→zones | Affected zone |
| sensor_id | int FK→sensors nullable | Source sensor |
| start_timestamp | datetime | Alarm start |
| end_timestamp | datetime nullable | Alarm end |
| description | text | Human-readable description |
| recommended_action | text | Recommended remediation |
| status | str | active, acknowledged, resolved |
| source | str | preexisting, detection |
| acknowledged_at | datetime nullable | Ack time |
| acknowledged_by | str nullable | Ack user |
| resolved_at | datetime nullable | Resolution time |
| resolved_by | str nullable | Resolution user |

## alarm_inventory_lots

| Column | Type | Description |
|--------|------|-------------|
| id | int PK | Primary key |
| alarm_id | int FK→alarms | Alarm |
| inventory_lot_id | int FK→inventory_lots | Affected lot |

## inspections

| Column | Type | Description |
|--------|------|-------------|
| id | int PK | Primary key |
| alarm_id | int FK→alarms | Related alarm |
| inspector_name | str | Inspector |
| inspection_timestamp | datetime | Scheduled time |
| status | str | pending, scheduled, completed, cancelled |
| findings | text nullable | Inspection findings |
| notes | text nullable | Additional notes |

## remediations

| Column | Type | Description |
|--------|------|-------------|
| id | int PK | Primary key |
| alarm_id | int FK→alarms | Related alarm |
| inspection_id | int FK→inspections nullable | Related inspection |
| action_type | str | Type of remediation action |
| description | text | Action description |
| performed_by | str | Who performed |
| performed_at | datetime | When performed |
| status | str | pending, in_progress, completed |

## ground_truth_anomalies

| Column | Type | Description |
|--------|------|-------------|
| id | int PK | Primary key |
| anomaly_type | str | Type of anomaly |
| entity_type | str | sensor_reading, door_event, sensor, inventory_lot, alarm |
| entity_id | int | Affected entity ID |
| description | text | Anomaly description |
| true_severity | str | critical, warning, info |
| injected_at | datetime | When injected |

> **Note:** This table is NEVER queried by detection logic. It is used only for evaluation metrics (precision/recall/F1).
