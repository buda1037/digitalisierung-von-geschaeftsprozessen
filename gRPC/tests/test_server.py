import sys
from concurrent import futures
from pathlib import Path

import grpc
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "generated"))
sys.path.insert(0, str(Path(__file__).parent.parent))

import wareneingang_pb2
import wareneingang_pb2_grpc

from server import WareneingangsServicer


@pytest.fixture
def stub():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    wareneingang_pb2_grpc.add_WareneingangsServiceServicer_to_server(
        WareneingangsServicer(), server
    )
    port = server.add_insecure_port("localhost:0")
    server.start()

    channel = grpc.insecure_channel(f"localhost:{port}")
    yield wareneingang_pb2_grpc.WareneingangsServiceStub(channel)

    channel.close()
    server.stop(None)


def test_erfasse_wareneingang_legt_eintrag_an(stub):
    antwort = stub.ErfasseWareneingang(
        wareneingang_pb2.ErfasseWareneingangRequest(
            retouren_id="RET-1", zustand=wareneingang_pb2.NEUWERTIG
        )
    )

    assert antwort.retouren_id == "RET-1"
    assert antwort.zustand == wareneingang_pb2.NEUWERTIG
    assert antwort.wareneingang_id
    assert antwort.erfasst_am


def test_erfasse_wareneingang_ohne_zustand_schlaegt_fehl(stub):
    with pytest.raises(grpc.RpcError) as exc_info:
        stub.ErfasseWareneingang(wareneingang_pb2.ErfasseWareneingangRequest(retouren_id="RET-1"))

    assert exc_info.value.code() == grpc.StatusCode.INVALID_ARGUMENT


def test_erfasse_wareneingang_doppelt_schlaegt_fehl(stub):
    stub.ErfasseWareneingang(
        wareneingang_pb2.ErfasseWareneingangRequest(
            retouren_id="RET-1", zustand=wareneingang_pb2.NEUWERTIG
        )
    )

    with pytest.raises(grpc.RpcError) as exc_info:
        stub.ErfasseWareneingang(
            wareneingang_pb2.ErfasseWareneingangRequest(
                retouren_id="RET-1", zustand=wareneingang_pb2.GETRAGEN
            )
        )

    assert exc_info.value.code() == grpc.StatusCode.ALREADY_EXISTS


def test_get_wareneingang_findet_erfassten_eintrag(stub):
    stub.ErfasseWareneingang(
        wareneingang_pb2.ErfasseWareneingangRequest(
            retouren_id="RET-1", zustand=wareneingang_pb2.BESCHAEDIGT, notiz="Riss"
        )
    )

    antwort = stub.GetWareneingang(wareneingang_pb2.GetWareneingangRequest(retouren_id="RET-1"))

    assert antwort.zustand == wareneingang_pb2.BESCHAEDIGT
    assert antwort.notiz == "Riss"


def test_get_wareneingang_unbekannte_retoure_not_found(stub):
    with pytest.raises(grpc.RpcError) as exc_info:
        stub.GetWareneingang(wareneingang_pb2.GetWareneingangRequest(retouren_id="unbekannt"))

    assert exc_info.value.code() == grpc.StatusCode.NOT_FOUND


def test_liste_wareneingaenge_filtert_nach_zustand(stub):
    stub.ErfasseWareneingang(
        wareneingang_pb2.ErfasseWareneingangRequest(
            retouren_id="RET-1", zustand=wareneingang_pb2.NEUWERTIG
        )
    )
    stub.ErfasseWareneingang(
        wareneingang_pb2.ErfasseWareneingangRequest(
            retouren_id="RET-2", zustand=wareneingang_pb2.GETRAGEN
        )
    )

    alle = list(stub.ListeWareneingaenge(wareneingang_pb2.ListeWareneingaengeRequest()))
    assert len(alle) == 2

    nur_getragen = list(
        stub.ListeWareneingaenge(
            wareneingang_pb2.ListeWareneingaengeRequest(zustand_filter=wareneingang_pb2.GETRAGEN)
        )
    )
    assert len(nur_getragen) == 1
    assert nur_getragen[0].retouren_id == "RET-2"


def test_korrigiere_zustand_aktualisiert_eintrag(stub):
    erfasst = stub.ErfasseWareneingang(
        wareneingang_pb2.ErfasseWareneingangRequest(
            retouren_id="RET-1", zustand=wareneingang_pb2.NEUWERTIG
        )
    )

    korrigiert = stub.KorrigiereZustand(
        wareneingang_pb2.KorrigiereZustandRequest(
            wareneingang_id=erfasst.wareneingang_id,
            neuer_zustand=wareneingang_pb2.BESCHAEDIGT,
        )
    )

    assert korrigiert.zustand == wareneingang_pb2.BESCHAEDIGT

    nachgefragt = stub.GetWareneingang(wareneingang_pb2.GetWareneingangRequest(retouren_id="RET-1"))
    assert nachgefragt.zustand == wareneingang_pb2.BESCHAEDIGT


def test_korrigiere_zustand_unbekannte_id_not_found(stub):
    with pytest.raises(grpc.RpcError) as exc_info:
        stub.KorrigiereZustand(
            wareneingang_pb2.KorrigiereZustandRequest(
                wareneingang_id="unbekannt", neuer_zustand=wareneingang_pb2.NEUWERTIG
            )
        )

    assert exc_info.value.code() == grpc.StatusCode.NOT_FOUND
