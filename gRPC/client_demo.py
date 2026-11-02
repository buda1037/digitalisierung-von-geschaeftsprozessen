import sys
from pathlib import Path

import grpc

sys.path.insert(0, str(Path(__file__).parent / "generated"))

import wareneingang_pb2
import wareneingang_pb2_grpc


def main():
    with grpc.insecure_channel("localhost:50051") as channel:
        stub = wareneingang_pb2_grpc.WareneingangsServiceStub(channel)

        print("-- ErfasseWareneingang --")
        w1 = stub.ErfasseWareneingang(
            wareneingang_pb2.ErfasseWareneingangRequest(
                retouren_id="RET-1001",
                zustand=wareneingang_pb2.NEUWERTIG,
                notiz="Originalverpackung, Etikett noch dran",
            )
        )
        print(w1)

        w2 = stub.ErfasseWareneingang(
            wareneingang_pb2.ErfasseWareneingangRequest(
                retouren_id="RET-1002",
                zustand=wareneingang_pb2.BESCHAEDIGT,
                notiz="Riss am Aermel",
            )
        )
        print(w2)

        print("-- GetWareneingang --")
        print(stub.GetWareneingang(wareneingang_pb2.GetWareneingangRequest(retouren_id="RET-1001")))

        print("-- ListeWareneingaenge (alle) --")
        for eintrag in stub.ListeWareneingaenge(wareneingang_pb2.ListeWareneingaengeRequest()):
            print(eintrag)

        print("-- KorrigiereZustand --")
        korrigiert = stub.KorrigiereZustand(
            wareneingang_pb2.KorrigiereZustandRequest(
                wareneingang_id=w2.wareneingang_id,
                neuer_zustand=wareneingang_pb2.GETRAGEN,
            )
        )
        print(korrigiert)


if __name__ == "__main__":
    main()
