"""Async gRPC server that mirrors key REST operations."""

from __future__ import annotations

import grpc
from google.protobuf import empty_pb2, struct_pb2

from smart_warehouse.server.api.schemas.simulation import PackageSchema, SimulationStateSchema
from smart_warehouse.services import SimulationService


class SimulationGrpcService:
    def __init__(self, service: SimulationService) -> None:
        self.service = service

    async def GetState(self, request: empty_pb2.Empty, context: grpc.aio.ServicerContext) -> struct_pb2.Struct:  # noqa: N802
        snapshot = self.service.snapshot(telemetry=[])
        layout = self.service.context.layout
        schema = SimulationStateSchema.from_domain(snapshot, layout)
        struct = struct_pb2.Struct()
        struct.update(schema.model_dump(mode="json"))
        return struct

    async def SpawnPackage(self, request: empty_pb2.Empty, context: grpc.aio.ServicerContext) -> struct_pb2.Struct:  # noqa: N802
        package = self.service.spawn_package()
        if not package:
            context.set_code(grpc.StatusCode.RESOURCE_EXHAUSTED)
            context.set_details("No available pickup zones to spawn a new package.")
            return struct_pb2.Struct()
        schema = PackageSchema.from_domain(package)
        struct = struct_pb2.Struct()
        struct.update(schema.model_dump(mode="json"))
        return struct


class _SimulationHandler(grpc.GenericRpcHandler):
    def __init__(self, servicer: SimulationGrpcService) -> None:
        self.servicer = servicer
        self._method_handlers = {
            "GetState": grpc.unary_unary_rpc_method_handler(
                servicer.GetState,
                request_deserializer=empty_pb2.Empty.FromString,
                response_serializer=struct_pb2.Struct.SerializeToString,
            ),
            "SpawnPackage": grpc.unary_unary_rpc_method_handler(
                servicer.SpawnPackage,
                request_deserializer=empty_pb2.Empty.FromString,
                response_serializer=struct_pb2.Struct.SerializeToString,
            ),
        }

    def service(self, handler_call_details: grpc.HandlerCallDetails):
        method = handler_call_details.method.rsplit("/", maxsplit=1)[-1]
        return self._method_handlers.get(method)


def create_grpc_server(service: SimulationService, port: int = 50051) -> grpc.aio.Server:
    server = grpc.aio.server()
    handler = _SimulationHandler(SimulationGrpcService(service))
    server.add_generic_rpc_handlers((handler,))
    server.add_insecure_port(f"[::]:{port}")
    return server


async def start_grpc_server(service: SimulationService, port: int = 50051) -> grpc.aio.Server:
    server = create_grpc_server(service, port)
    await server.start()
    return server
