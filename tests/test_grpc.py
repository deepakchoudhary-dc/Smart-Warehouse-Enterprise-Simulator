import grpc
import pytest
from google.protobuf import empty_pb2
from google.protobuf import struct_pb2

from smart_warehouse.server.dependencies import reset_simulation_service
from smart_warehouse.server.grpc.server import create_grpc_server
from smart_warehouse.services import SimulationService


@pytest.mark.asyncio
async def test_grpc_get_state_and_spawn(tmp_path):
    reset_simulation_service()
    service = SimulationService()
    server = create_grpc_server(service, port=50070)
    await server.start()
    try:
        async with grpc.aio.insecure_channel("localhost:50070") as channel:
            get_state = channel.unary_unary(
                "/smartwarehouse.Simulation/GetState",
                request_serializer=empty_pb2.Empty.SerializeToString,
                response_deserializer=struct_pb2.Struct.FromString,
            )
            state = await get_state(empty_pb2.Empty())
            assert "packages" in state
            packages_value = state["packages"]
            if hasattr(packages_value, "list_value"):
                assert packages_value.list_value is not None
            else:
                assert isinstance(packages_value, struct_pb2.ListValue)

            spawn = channel.unary_unary(
                "/smartwarehouse.Simulation/SpawnPackage",
                request_serializer=empty_pb2.Empty.SerializeToString,
                response_deserializer=struct_pb2.Struct.FromString,
            )
            package = await spawn(empty_pb2.Empty())
            status_value = package["status"]
            if hasattr(status_value, "string_value"):
                assert status_value.string_value == "queued"
            else:
                assert status_value == "queued"
    finally:
        await server.stop(0)
