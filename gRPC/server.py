import datetime
import sys
import threading
import uuid
from concurrent import futures
from pathlib import Path

import grpc

sys.path.insert(0, str(Path(__file__).parent / "generated"))

import wareneingang_pb2
import wareneingang_pb2_grpc


class WareneingangsServicer(wareneingang_pb2_grpc.WareneingangsServiceServicer):
    def __init__(self):
        self._lock = threading.Lock()
        self._by_retouren_id = {}
        self._by_id = {}

    def ErfasseWareneingang(self, request, context):
        if not request.retouren_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "retouren_id darf nicht leer sein")
        if request.zustand == wareneingang_pb2.ZUSTAND_UNBEKANNT:
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "zustand muss gesetzt sein (NEUWERTIG, BESCHAEDIGT oder GETRAGEN)",
            )

        with self._lock:
            if request.retouren_id in self._by_retouren_id:
                context.abort(
                    grpc.StatusCode.ALREADY_EXISTS,
                    f"Wareneingang fuer retouren_id '{request.retouren_id}' bereits erfasst "
                    "- nutze KorrigiereZustand zum Aendern",
                )

            eintrag = wareneingang_pb2.Wareneingang(
                wareneingang_id=str(uuid.uuid4()),
                retouren_id=request.retouren_id,
                zustand=request.zustand,
                notiz=request.notiz,
                erfasst_am=datetime.datetime.now(datetime.UTC).isoformat(),
            )
            self._by_retouren_id[request.retouren_id] = eintrag
            self._by_id[eintrag.wareneingang_id] = eintrag

        return eintrag

    def GetWareneingang(self, request, context):
        with self._lock:
            eintrag = self._by_retouren_id.get(request.retouren_id)

        if eintrag is None:
            context.abort(
                grpc.StatusCode.NOT_FOUND,
                f"Keine Erfassung fuer retouren_id '{request.retouren_id}' gefunden",
            )

        return eintrag

    def ListeWareneingaenge(self, request, context):
        with self._lock:
            eintraege = list(self._by_retouren_id.values())

        for eintrag in eintraege:
            if (
                request.zustand_filter != wareneingang_pb2.ZUSTAND_UNBEKANNT
                and eintrag.zustand != request.zustand_filter
            ):
                continue
            yield eintrag

    def KorrigiereZustand(self, request, context):
        if request.neuer_zustand == wareneingang_pb2.ZUSTAND_UNBEKANNT:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "neuer_zustand muss gesetzt sein")

        with self._lock:
            eintrag = self._by_id.get(request.wareneingang_id)
            if eintrag is None:
                context.abort(
                    grpc.StatusCode.NOT_FOUND,
                    f"Kein Wareneingang mit id '{request.wareneingang_id}' gefunden",
                )
            assert eintrag is not None

            aktualisiert = wareneingang_pb2.Wareneingang()
            aktualisiert.CopyFrom(eintrag)
            aktualisiert.zustand = request.neuer_zustand

            self._by_id[aktualisiert.wareneingang_id] = aktualisiert
            self._by_retouren_id[aktualisiert.retouren_id] = aktualisiert

        return aktualisiert


def serve(port: int = 50051):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    wareneingang_pb2_grpc.add_WareneingangsServiceServicer_to_server(
        WareneingangsServicer(), server
    )
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"WareneingangsService laeuft auf Port {port}")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
