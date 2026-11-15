"""Use cases — re-exported for presentation layer."""
from .catalog import (
    CreateProductUseCase,
    CreateStoreUseCase,
    GetProductUseCase,
    ListProductsUseCase,
    UpdateProductUseCase,
)
from .history import GetHistoryUseCase, ListHistoryUseCase
from .operations import (
    CancelFBSReservationUseCase,
    CreateFBOShipmentUseCase,
    CreateTransferUseCase,
    DispatchFBOShipmentUseCase,
    DispatchTransferUseCase,
    ReceiveFBOShipmentUseCase,
    ReceiveStockUseCase,
    ReceiveTransferUseCase,
    ReserveFBSStockUseCase,
    ShipFBSOrderUseCase,
)
from .shipments import ListReservationsUseCase, ListShipmentsUseCase, ListTransfersUseCase
from .stocks import GetInTransitUseCase, GetStockBySkuUseCase, GetStocksOverviewUseCase
from .warehouses import (
    ArchiveWarehouseUseCase,
    CreateWarehouseUseCase,
    GetWarehouseUseCase,
    ListWarehousesUseCase,
    RenameWarehouseUseCase,
)
from .wildberries import GetWildberriesStatusUseCase, SyncWildberriesUseCase

__all__ = [
    "CreateProductUseCase",
    "CreateStoreUseCase",
    "GetProductUseCase",
    "ListProductsUseCase",
    "UpdateProductUseCase",
    "GetHistoryUseCase",
    "ListHistoryUseCase",
    "CancelFBSReservationUseCase",
    "CreateFBOShipmentUseCase",
    "CreateTransferUseCase",
    "DispatchFBOShipmentUseCase",
    "DispatchTransferUseCase",
    "ReceiveFBOShipmentUseCase",
    "ReceiveStockUseCase",
    "ReceiveTransferUseCase",
    "ReserveFBSStockUseCase",
    "ShipFBSOrderUseCase",
    "ListShipmentsUseCase",
    "ListReservationsUseCase",
    "ListTransfersUseCase",
    "GetInTransitUseCase",
    "GetStockBySkuUseCase",
    "GetStocksOverviewUseCase",
    "ArchiveWarehouseUseCase",
    "CreateWarehouseUseCase",
    "GetWarehouseUseCase",
    "ListWarehousesUseCase",
    "RenameWarehouseUseCase",
    "GetWildberriesStatusUseCase",
    "SyncWildberriesUseCase",
]
