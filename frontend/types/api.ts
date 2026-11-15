// All TypeScript interfaces matching the CheckStock backend API contract.
// UUIDs and timestamps are serialized as strings by the JSON API.

export interface Product {
  id: string
  store_id: string
  sku: string
  name: string
  wb_external_id: string | null
}

export interface Warehouse {
  id: string
  name: string
  is_active: boolean
  archived_at: string | null
}

export interface StockOut {
  product_id: string
  warehouse_id: string
  physical: number
  reserved: number
  available: number
  version: number
}

export type ReservationStatus = 'ACTIVE' | 'CANCELLED' | 'SHIPPED'
export type TransferStatus = 'DRAFT' | 'IN_TRANSIT' | 'RECEIVED' | 'CANCELLED'
export type ShipmentType = 'FBS' | 'FBO'
export type ShipmentStatus = 'DRAFT' | 'IN_TRANSIT' | 'SHIPPED' | 'RECEIVED' | 'CANCELLED'

export interface Reservation {
  id: string
  product_id: string
  warehouse_id: string
  quantity: number
  status: ReservationStatus
  created_at: string | null
  cancelled_at: string | null
  shipped_at: string | null
}

export interface TransferItem {
  product_id: string
  quantity: number
}

export interface Transfer {
  id: string
  source_warehouse_id: string
  target_warehouse_id: string
  status: TransferStatus
  items: TransferItem[]
  created_at: string | null
  dispatched_at: string | null
  received_at: string | null
}

export interface ShipmentItem {
  product_id: string
  quantity: number
}

export interface Shipment {
  id: string
  type: ShipmentType
  source_warehouse_id: string
  status: ShipmentStatus
  destination: string | null
  external_status: string | null
  reservation_id: string | null
  items: ShipmentItem[]
  created_at: string | null
  dispatched_at: string | null
  received_at: string | null
}

export interface HistoryEntry {
  operation_id: string
  operation_type: string
  status: string
  created_at: string
  product_id: string | null
  sku: string | null
  product_name: string | null
  quantity: number
  source_warehouse_id: string | null
  source_warehouse_name: string | null
  target_warehouse_id: string | null
  target_warehouse_name: string | null
  related_entity_type: string | null
  related_entity_id: string | null
}

export interface WarehouseStockRow {
  warehouse_id: string
  warehouse_name: string
  physical: number
  reserved: number
  available: number
}

export interface InTransit {
  transfer: number
  fbo: number
  fbs: number
}

export interface StockRow {
  product_id: string
  sku: string
  name: string
  wb_external_id: string | null
  warehouses: WarehouseStockRow[]
  total_physical: number
  total_reserved: number
  total_available: number
  in_transit: InTransit
  in_transit_total: number
}

export interface StocksOverview {
  warehouses: Warehouse[]
  products: StockRow[]
}

export interface InTransitRow {
  product_id: string
  sku: string
  name: string
  transfer: number
  fbo: number
  fbs: number
  total: number
}

export interface InTransitResponse {
  items: InTransitRow[]
}

export interface PaginatedProducts {
  items: Product[]
  total: number
}

export interface PaginatedHistory {
  items: HistoryEntry[]
  total: number
}

export interface PaginatedShipments {
  items: Shipment[]
  total: number
}

export interface ReservationView {
  id: string
  product_id: string
  warehouse_id: string
  sku: string
  product_name: string
  warehouse_name: string
  quantity: number
  status: ReservationStatus
  created_at: string | null
}

export interface TransferItemView {
  product_id: string
  sku: string
  quantity: number
}

export interface TransferView {
  id: string
  source_warehouse_id: string
  source_warehouse_name: string
  target_warehouse_id: string
  target_warehouse_name: string
  status: TransferStatus
  items: TransferItemView[]
  created_at: string | null
  dispatched_at: string | null
  received_at: string | null
}

// ---- Requests ----

export interface ItemLine {
  product_id: string
  quantity: number
}

export interface CreateProductRequest {
  sku: string
  name: string
  wb_external_id?: string | null
}

export interface UpdateProductRequest {
  name?: string | null
  sku?: string | null
  wb_external_id?: string | null
}

export interface CreateWarehouseRequest {
  name: string
}

export interface RenameWarehouseRequest {
  name: string
}

export interface ReceiveStockRequest {
  warehouse_id: string
  product_id: string
  quantity: number
}

export interface ReserveStockRequest {
  warehouse_id: string
  product_id: string
  quantity: number
}

export interface ShipFBSRequest {
  reservation_id: string
}

export interface CreateTransferRequest {
  source_warehouse_id: string
  target_warehouse_id: string
  items: ItemLine[]
}

export interface CreateFBORequest {
  source_warehouse_id: string
  items: ItemLine[]
}

// ---- Structured error details ----

export interface OtherWarehouse {
  warehouse_id: string
  name: string
  available: number
}

export interface ShortageDetail {
  product_id: string
  sku: string
  warehouse_id: string
  requested: number
  available: number
  shortfall: number
  other_warehouses: OtherWarehouse[]
  suggestion: string
}

export interface NonZeroStockDetail {
  product_id: string
  sku: string
  name: string
  physical: number
}

export interface ArchiveDetail {
  warehouse_id: string
  reasons: string[]
  nonzero_stocks: NonZeroStockDetail[]
}

// ---- Wildberries ----

export interface WbLastSync {
  status: string
  items_processed: number
  error: string | null
  started_at: string | null
  finished_at: string | null
}

export interface WbStatus {
  configured: boolean
  demo_mode: boolean
  last_sync: WbLastSync | null
}

export interface WbSyncResult {
  status: string
  demo_mode: boolean
  message?: string
  items_processed?: number
  error?: string | null
}
