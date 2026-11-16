import type {
  CreateFBORequest,
  CreateProductRequest,
  CreateTransferRequest,
  CreateWarehouseRequest,
  InTransitResponse,
  PaginatedHistory,
  PaginatedProducts,
  PaginatedShipments,
  Product,
  ReceiveStockRequest,
  RenameWarehouseRequest,
  Reservation,
  ReservationView,
  ReserveStockRequest,
  ShipFBSRequest,
  Shipment,
  StockOut,
  StocksOverview,
  Transfer,
  TransferView,
  UpdateProductRequest,
  Warehouse,
  WbStatus,
  WbSyncResult,
} from '~/types/api'

type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'DELETE'

export type Query = Record<string, string | number | boolean | undefined>

interface ErrorEnvelope {
  error: {
    code: string
    message: string
    detail?: unknown
  }
}

/** Normalized API error thrown by every request helper. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly detail: unknown

  constructor(status: number, code: string, message: string, detail?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.detail = detail
  }
}

function extractEnvelope(data: unknown): ErrorEnvelope['error'] | null {
  if (typeof data !== 'object' || data === null) return null
  const maybeError = (data as { error?: unknown }).error
  if (typeof maybeError !== 'object' || maybeError === null) return null
  const err = maybeError as { code?: unknown; message?: unknown; detail?: unknown }
  if (typeof err.code === 'string' && typeof err.message === 'string') {
    return { code: err.code, message: err.message, detail: err.detail }
  }
  return null
}

function normalizeError(err: unknown): ApiError {
  if (err instanceof ApiError) return err
  const e = err as { status?: number; statusCode?: number; data?: unknown; message?: string }
  const status = e?.status ?? e?.statusCode ?? 0
  const envelope = extractEnvelope(e?.data)
  if (envelope) {
    return new ApiError(status, envelope.code, envelope.message, envelope.detail)
  }
  return new ApiError(status, 'network_error', e?.message ?? 'Ошибка сети или сервера')
}

function cleanQuery(query?: Query): Record<string, string> | undefined {
  if (!query) return undefined
  const out: Record<string, string> = {}
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === '') continue
    out[key] = String(value)
  }
  return out
}

/**
 * Typed API client built on top of `$fetch` (ofetch). All methods return typed
 * data and throw a normalized `ApiError` on non-2xx responses.
 */
export function useApi() {
  const config = useRuntimeConfig()
  const base = (config.public as { apiBase: string }).apiBase
  // During SSR use the request-bound fetch so relative /api paths resolve to
  // the running Nitro server (which proxies to the backend). On the client it
  // behaves like the global $fetch.
  const fetchBase = useRequestFetch()

  async function request<T>(
    path: string,
    method: HttpMethod,
    opts: { query?: Query; body?: unknown } = {},
  ): Promise<T> {
    const url = `${base}${path}`
    const query = cleanQuery(opts.query)
    try {
      if (method === 'GET') {
        return await fetchBase<T>(url, { method, query })
      }
      return await fetchBase<T>(url, { method, body: opts.body as Record<string, unknown> })
    } catch (err) {
      throw normalizeError(err)
    }
  }

  return {
    // Products
    listProducts: (query?: Query) => request<PaginatedProducts>('/products', 'GET', { query }),
    createProduct: (body: CreateProductRequest) => request<Product>('/products', 'POST', { body }),
    updateProduct: (id: string, body: UpdateProductRequest) =>
      request<Product>(`/products/${id}`, 'PATCH', { body }),

    // Warehouses
    listWarehouses: () => request<Warehouse[]>('/warehouses', 'GET'),
    createWarehouse: (body: CreateWarehouseRequest) => request<Warehouse>('/warehouses', 'POST', { body }),
    renameWarehouse: (id: string, body: RenameWarehouseRequest) =>
      request<Warehouse>(`/warehouses/${id}`, 'PATCH', { body }),
    archiveWarehouse: (id: string) => request<Warehouse>(`/warehouses/${id}`, 'DELETE'),
    purgeWarehouse: (id: string) => request<Warehouse>(`/warehouses/${id}/purge`, 'DELETE'),

    // Stocks
    getStocks: (query?: Query) => request<StocksOverview>('/stocks', 'GET', { query }),
    getInTransit: () => request<InTransitResponse>('/stocks/in-transit', 'GET'),

    // Operations
    receiveStock: (body: ReceiveStockRequest) => request<StockOut>('/operations/receipts', 'POST', { body }),
    reserveStock: (body: ReserveStockRequest) => request<Reservation>('/operations/reservations', 'POST', { body }),
    cancelReservation: (id: string) => request<Reservation>(`/operations/reservations/${id}/cancel`, 'POST'),
    createTransfer: (body: CreateTransferRequest) => request<Transfer>('/operations/transfers', 'POST', { body }),
    dispatchTransfer: (id: string) => request<Transfer>(`/operations/transfers/${id}/dispatch`, 'POST'),
    receiveTransfer: (id: string) => request<Transfer>(`/operations/transfers/${id}/receive`, 'POST'),
    shipFbs: (body: ShipFBSRequest) => request<Shipment>('/operations/shipments/fbs', 'POST', { body }),
    createFbo: (body: CreateFBORequest) => request<Shipment>('/operations/shipments/fbo', 'POST', { body }),
    dispatchShipment: (id: string) => request<Shipment>(`/operations/shipments/${id}/dispatch`, 'POST'),
    receiveShipment: (id: string) => request<Shipment>(`/operations/shipments/${id}/receive`, 'POST'),

    // Listings
    listReservations: (status?: string) =>
      request<ReservationView[]>('/reservations', 'GET', { query: { status } }),
    listTransfers: (status?: string) => request<TransferView[]>('/transfers', 'GET', { query: { status } }),

    // Shipments listing
    listShipments: (query?: Query) => request<PaginatedShipments>('/shipments', 'GET', { query }),

    // History
    listHistory: (query?: Query) => request<PaginatedHistory>('/history', 'GET', { query }),

    // Wildberries
    getWbStatus: () => request<WbStatus>('/integrations/wb/status', 'GET'),
    syncWb: () => request<WbSyncResult>('/integrations/wb/sync', 'POST'),
  }
}
