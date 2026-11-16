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
    PurgeWarehouseUseCase,
    RenameWarehouseUseCase,
)
from .wildberries import GetWildberriesStatusUseCase, SyncWildberriesUseCase

__all__ = [
    "ArchiveWarehouseUseCase",
    "CancelFBSReservationUseCase",
    "CreateFBOShipmentUseCase",
    "CreateProductUseCase",
    "CreateStoreUseCase",
    "CreateTransferUseCase",
    "CreateWarehouseUseCase",
    "DispatchFBOShipmentUseCase",
    "DispatchTransferUseCase",
    "GetHistoryUseCase",
    "GetInTransitUseCase",
    "GetProductUseCase",
    "GetStockBySkuUseCase",
    "GetStocksOverviewUseCase",
    "GetWarehouseUseCase",
    "GetWildberriesStatusUseCase",
    "ListHistoryUseCase",
    "ListProductsUseCase",
    "ListReservationsUseCase",
    "ListShipmentsUseCase",
    "ListTransfersUseCase",
    "ListWarehousesUseCase",
    "PurgeWarehouseUseCase",
    "ReceiveFBOShipmentUseCase",
    "ReceiveStockUseCase",
    "ReceiveTransferUseCase",
    "RenameWarehouseUseCase",
    "ReserveFBSStockUseCase",
    "ShipFBSOrderUseCase",
    "SyncWildberriesUseCase",
    "UpdateProductUseCase",
]
