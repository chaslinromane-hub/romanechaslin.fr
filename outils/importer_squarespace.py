"""
Import unique des photos de l'ancien site Squarespace (romanechaslin.fr).

Télécharge chaque photo dans `_import_squarespace/` (ignoré par git),
puis les optimise et remplit `contenu/photos.json` et `contenu/galeries.json`.
Ce script n'a besoin d'être lancé qu'une fois.
"""

from __future__ import annotations

import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import photos as P  # noqa: E402

CDN = "https://images.squarespace-cdn.com/content/v1/65552d4410f11306ebf66cda/"
DOSSIER = P.RACINE / "_import_squarespace"

GALERIES = {
    "concert": """
9da98ef3-d22e-464d-9c4c-14a2901856fe/DSC_0100-Enhanced-NR.jpg
697b5f17-88b6-4dcc-9463-b925db432137/GAZO-12.jpg
086e7b6d-d9d1-4331-a1db-9a786db04cf6/DSC_4068-co.jpg
b2041d26-b074-47f7-81d8-467d9e03b374/DSC_4037.jpg
90e81dde-a227-4251-939d-e0eec39304cb/DSC_3403.jpg
10def334-ec60-40ac-ae36-3c9dc639fd35/FATOUMATA+DIAWARA-1.jpg
a8dcbbdf-a3f5-40af-b708-3ff7f8593aa7/DSC_5406.jpg
24939576-b852-4e8e-bdab-2ec0588a3073/DSC_0284-Enhanced-NR.jpg
4f7bec4d-97fd-411d-893b-1aae974674e2/JOLAGREEN-6.jpg
ce4bcd62-3e61-4d4d-bd31-d062e6d5160b/THE+MURDER+CAPITAL-5.jpg
1bfa2247-010c-4a00-ac38-4ec8eb4b4d66/DSC_5958.jpg
30c9f9ee-1178-48ac-845b-392d9f41ee10/DSC_7010-Enhanced-NR.jpg
5478a5dc-ed10-483c-8718-7c0f6e98d40e/DSC_0360.jpg
d8094b3e-c609-4f35-8f6c-389b468d9609/DSC_6943-Enhanced-NR.jpg
b4de2469-e98a-4b48-8e11-abbb8fdb7c7a/JOLAGREEN-5.jpg
6daf4727-dd96-48fe-aea6-c3d64a99a4cb/DSC_2354.jpg
9b5757e8-382a-415a-9f96-e90381ba0500/DSC_7824.jpg
6006838b-8a92-45ff-bb09-568bfc04f2c5/DSC_3949.jpg
94bc702a-8ef9-4447-ba18-3529f983f296/DSC_5387.jpg
0d79882d-7e06-42ae-b198-53073612027e/DSC_0826.jpg
2ffcd907-bbef-4999-ae48-bfc1b318c516/DSC_5861-2.jpg
290486b0-883d-43e9-809d-7c4dfcc47c69/DSC_7851-Enhanced-NR.jpg
46606b4d-b136-45df-9a1c-479fdb524405/DSC_6250.jpg
aa87367f-e6c7-481e-bdc2-ec09f0425a3f/DSC_1761-3.jpg
8e1bef10-d241-4ef9-829b-bf02a0cdc63c/DSC_0241.jpg
bba5628e-fc0f-456b-b9f2-890520e7bd78/DSC_5546.jpg
1cfeedf9-8992-40bf-a30d-aa8be3a31402/DSC_7462-Enhanced-NR.jpg
b24c01fa-97d0-4405-a924-abc6ca7eed71/DSC_0156-Enhanced-NR-2.jpg
170f3d35-9056-4402-a955-962e57cc4fa2/DSC_1071.jpg
cebbdf59-6982-4f3c-bf94-4f8f67d969d9/GAZO-8.jpg
b28d11ec-58e6-4206-aa5c-d263fb7f0457/ADF-2.jpg
03ecee7b-8c0c-4b6b-a0f0-8657cf970293/DSC_0919.jpg
b4c22673-52e4-4eb5-b766-11e8ab4fe336/DSC_0420+copie.jpg
ad476b60-8eab-4ae1-b66a-f46416a76e3e/DSC_2077.jpg
65471e1d-5491-4096-af57-d6031b7dfb05/Capture+d%E2%80%99%C3%A9cran+2026-04-12+%C3%A0+18.09.05.png
6110b33d-b698-47ee-8b18-3b8757599868/DSC_2585.jpg
d6d07953-990e-426f-82c1-daca6e484e81/DSC_3370.jpg
908f85ea-e55b-4df9-9778-d9d1ceb083cd/DSC_3078.jpg
e2df33cf-ccdf-4899-90d4-5ec708ce8006/DSC_3947.jpg
2a70dcc6-dff3-43a7-b382-7b83a30099db/THE+MURDER+CAPITAL-3.jpg
1c3c7070-1298-4acb-9500-73436d4ce671/DSC_6810-Enhanced-NR.jpg
6f44df7c-f568-401d-b441-bb86d38aa4fd/DSC_8108+copie.png
e5c6e92c-9a7b-46b3-acc0-8a15528f948b/DSC_2387.jpg
a54521f4-e29d-42d1-99bf-275be4fb7e27/DSC_7749.jpg
e06ed3d1-6ad0-455e-bea7-8fccaf127dbe/DSC_7568.jpg
ea4ff8d0-eae3-4120-9bc2-0192bf90f7d7/DSC_0887-2.jpg
d0a2b8c8-5c57-4cf6-8570-a1f91c391110/DSC_2477.jpg
6313dcae-ee67-44cd-a84e-7bb4a45a0e54/DSC_6445.png
""",
    "corporate": """
332e6104-0217-4d06-a27b-af29c757a92c/DSC_5898-2.jpg
d78d54f9-e301-47d1-b1d2-634d703f8cd0/DSC_5803.jpg
eed9e9b9-56fb-4072-96c2-fab7709782d2/DSC_5905-2.jpg
32e62624-cd33-4d2c-a419-849d2b9df483/DSC_5875-2.jpg
ba12671e-821f-42b3-a42d-377c23bad522/DSC_5787.jpg
e35ba2a8-a46b-4bf4-985e-bd2d5d6e3e63/DSC_5839-2.jpg
89b82485-41d4-4d2c-9300-d68da9958856/DSC_5796.jpg
a33e90f6-9a61-4b1f-81c7-c95c5ed14247/DSC_6308.jpg
5212d425-78e6-4d45-b780-19a04eda0155/DSC_6063.jpg
0fa5a350-0a34-428c-a2ed-3098448eba80/DSC_6181.jpg
af470480-4fb5-48b3-901e-e81086097f3f/DSC_6234.jpg
adfa7d0a-4669-4eb3-93ea-675225e9aeac/DSC_6050.jpg
0c0d541c-4655-47da-a644-76a00ad0f6e0/DSC_6289.jpg
11302fcb-49d5-40d8-a549-45e363221846/DSC_6019.jpg
bf2b43eb-a1fb-4ed5-ad9a-a520b8974203/DSC_5943.jpg
3726ec57-bfd4-4c5a-8a34-b999ef3eef68/DSC_6178.jpg
44da6405-c81c-4c8f-9e40-255bed0b0b49/DSC_6029.jpg
""",
    "reportage": """
d48af46c-1bd7-4743-b1c9-4e733a40849c/DJI_0072-2.jpg
c439fae1-71de-4631-9339-d14651b3bb06/DSC_1902-Enhanced-NR.jpg
1c24c33c-8401-4951-b991-f53755834c0c/DSC_1406-Enhanced-NR.jpg
4a5bfd3f-d690-4afe-bfb6-5e1d9f35e1d1/DSC_1714+version+2.jpg
ead53139-9a14-479a-840d-66cd8b6f9c8c/DSC_1968-Enhanced-NR.jpg
81bbdbf1-03ee-4e72-8dcd-424f492e8bbc/DSC_2280-Enhanced-NR.jpg
bc5a8b54-5c70-4d9f-8cda-102d88ba184c/DSC_1364.jpg
a44d0e1b-2ab4-43d3-8a71-4a69b16947ef/DSC_2545-Enhanced-NR.jpg
55389595-0e61-48ba-b97e-963711764bb8/DSC_1462-2.jpg
28eda84e-5022-422e-a614-7377433bda94/DSC_1983-Enhanced-NR.jpg
ead5d80f-20af-4d3e-8116-8314e5513663/DSC_2309-Enhanced-NR.jpg
045c44e8-b0ba-4cda-afda-f9d37a5a7f44/DSC_2031.jpg
a642b3bf-28f4-4957-b8ac-d387ac9b7e93/DSC_1654-Enhanced-NR.jpg
1ad4dd7d-bcc5-4958-814f-48e005efb63c/DSC_1441.jpg
6b41dc01-5d77-4446-8bde-e148a98a9198/DSC_1469.jpg
1dc44dea-3e47-4fdc-bbc0-52cc56b0d0e3/DSC_2772.jpg
1d78ceec-e616-4370-a04b-67c753383f0a/DSC_1391-Enhanced-NR.jpg
b7f063e7-3d61-4654-866e-6eaf9bdf38ea/DJI_0108.jpg
e8f5489d-1978-4e5a-bdb0-43d588d5383d/DSC_2455-Enhanced-NR.jpg
""",
    "portrait": """
e03c8bcf-9088-4fd4-86c5-ed9e5e289dad/DSC_2066.jpg
53a7a7cf-6032-4cc8-968c-5c35e6e1d850/DSC_9738.jpg
b0e29706-ddbe-4444-be47-7610e152fe70/DSC_2256.jpg
a8585cb2-7c31-4970-bd30-9d7d55c6d821/DSC_8585.jpg
0c14e08b-1790-456d-b633-4059b7055df4/DSC_8431.jpg
35366e1e-a797-441a-9c0b-ee970d8c6b75/DSC_2151.jpg
7521cd78-c64d-4634-810f-cb81407b3068/DSC_2735.jpg
418e6ad0-e59e-4c88-845d-51265717007c/DSC_2063.jpg
1f55a7fe-515d-44e8-b5c0-3da450b5a907/DSC_8580.jpg
e24525b8-4d8e-439e-82dd-024ad9e22a97/DSC_4131.jpg
a0672737-a38c-4ed7-a633-db5b66db9349/DSC_2434.jpg
134e6815-0dfc-4c92-bd09-53aeac7ec75a/DSC_9838.jpg
5713aef5-040a-4d9d-8330-560244cca1d5/DSC_4056.jpg
86babf6a-5db3-44b1-8a01-8ad28ee723b5/DSC_2407.jpg
87684886-de6e-4403-b570-00904dddd79a/DSC_9891.jpg
5370376f-6723-4b97-9866-8d33ab9e0f08/DSC_4089.jpg
aa905f7f-40e0-498f-846a-0529acde9d39/DSC_8533.jpg
0e5e0073-b9d5-4bef-9d46-7549b5488199/DSC_3977.jpg
24d7be88-9cdb-4e2b-892c-32b5f3f4f5ec/DSC_2467.jpg
""",
    "portrait-professionnel": """
8a2fbd9a-3964-455f-bd4c-ff6fe1eea1df/C4.jpg
a17a561b-68ad-410b-8097-11b222db644b/DSC_9094+copie.jpg
02dfb1f5-7973-488b-8ee1-f9add550d4ec/DSC_9111.jpg
958ce82e-06c5-4d5f-92e3-efdf060f6b0a/NB1.jpg
ab7d27c2-7ac3-4982-bd6a-33b7b0407d5b/NB2.jpg
853cb9d1-5717-4614-99f4-cad08b26057c/C1.jpg
7240e76b-f806-405e-8717-b194124faf6b/C3.jpg
d31c12c2-c812-4cb1-9b7e-aca5eb70b111/DSC_4490.jpg
3ce1c018-0da8-4599-bf91-6ab165c8b843/DSC_4483.jpg
""",
    "tourisme": """
02867f3f-7aeb-4529-b7e1-a4d3f84c588d/000982620017.jpg
5b2c33a2-c1a4-4cad-9576-5a53704886da/Capture+d%E2%80%99%C3%A9cran+2023-11-20+%C3%A0+19.11.49.png
6916253c-ae55-4e0b-8628-9341863e0a0a/P17_9962.jpg
2fd9b5fd-bfa6-4afb-8d2c-c9d891486fee/000982620022.jpg
6a2154fb-c74f-4b0a-a7ec-f309ac871e19/P17_9791-2-01-01.jpeg
94663783-4023-4434-a03c-b6ffccd668c7/DSC_0510.jpg
076ea762-7e58-47bc-a8ab-d4f7268609e1/DSC_0211.jpg
5cb4c1ae-0826-46c8-9409-12756eb3b8f9/tempImageFvioBO.jpg
4b6138de-02da-4025-93f3-ae39bb766616/022A1424+2.JPG
ad179688-a6a5-4090-ba6b-eb13b62c98e8/DSC_0118.jpg
ff854c78-f032-4915-9e22-873a7fddd412/tempImagemYlpcH.jpg
9c524e88-82cc-44f1-ac13-eebda4031de7/tempImagelcnvzC.jpg
7065b612-9b2b-4436-ae10-966dd8a83281/P17_0520-2.jpg
b63f8d38-c1c3-4a54-8696-a47fdce08e1d/image-asset.jpeg
e21aad7a-f3af-479c-8d54-36f6b82cd407/DSC_0107.jpg
4cc67db9-60b9-42fd-9f50-2b3f3fe7b047/tempImageSHgClo.jpg
7417cb2a-848b-4094-9804-26ef61982bd3/IMG_6740+2.jpg
8eb1d9ef-0695-40b8-b4bf-58bb3cef160d/Capture+d%E2%80%99%C3%A9cran+2023-11-20+%C3%A0+19.04.54.png
d38eefe8-e907-4e0e-adcc-878509fc491d/tempImagecOG1Jb.jpg
e0095630-406b-427a-b6b6-6b79b85f86cb/Final+.jpg
a7fa2976-2694-4f6e-bd27-978d30dbf591/tempImagenjvdZe.jpg
cc911290-8118-4394-912a-bc9e706cc4cb/FullSizeRender+6.jpg
00cb2e93-cd42-4989-a3c4-9ea5d78d8899/P17_0530+copie.jpg
""",
}

# Photos utilisées hors galeries (accueil, couvertures, à propos).
AUTRES = """
018a2047-961b-481d-a31a-404c6b3f79e8/DSC_1117-Enhanced-NR.jpg
1a9b5980-2de3-4318-a4d7-9dfcf7c9436a/P17_9796-01.jpg
499e9a4c-76b2-496b-9e4a-313f832201df/DSC_0151-Enhanced-NR.jpg
baaaa8fc-140d-4086-9c2c-2d52419e9b79/DSC_0844-Enhanced-NR.jpg
65428569-ca03-40fc-9553-69a940d334e0/DSC_9068+copie.jpg
be3c16f2-c971-40b5-a804-8cded889d95c/DSC_8552.jpg
e2eb7973-f743-4cd9-9c09-4caaaedad5e6/AUR+jeudi+web-1181.jpg
"""

# Identifiants plus lisibles pour quelques fichiers au nom peu parlant.
RENOMMER = {
    "capture-decran-2026-04-12-a-18-09-05": "concert-capture",
    "capture-decran-2023-11-20-a-19-11-49": "voyage-capture-1",
    "capture-decran-2023-11-20-a-19-04-54": "voyage-capture-2",
    "image-asset": "voyage-image",
    "final": "voyage-final",
    "aur-jeudi-web-1181": "romane-portrait",
}


def lignes(bloc: str) -> list[str]:
    return [l.strip() for l in bloc.strip().splitlines() if l.strip()]


def pid_de(chemin: str) -> str:
    nom = urllib.parse.unquote(chemin.split("/")[-1].replace("+", " "))
    pid = P.identifiant(nom)
    return RENOMMER.get(pid, pid)


def telecharger(chemin: str) -> Path:
    pid = pid_de(chemin)
    ext = Path(chemin).suffix.lower()
    cible = DOSSIER / f"{pid}{ext}"
    if not cible.exists():
        url = CDN + chemin + "?format=2500w"
        with urllib.request.urlopen(url, timeout=60) as r:
            cible.write_bytes(r.read())
    return cible


def main() -> None:
    DOSSIER.mkdir(exist_ok=True)
    tous = {}
    for bloc in [*GALERIES.values(), AUTRES]:
        for chemin in lignes(bloc):
            tous.setdefault(pid_de(chemin), chemin)

    print(f"Téléchargement de {len(tous)} photos…")
    with ThreadPoolExecutor(8) as pool:
        fichiers = dict(zip(tous, pool.map(telecharger, tous.values())))

    photos = P.charger(P.FICHIER_PHOTOS)
    a_traiter = [(f, pid) for pid, f in fichiers.items() if not (P.DOSSIER_PHOTOS / f"{pid}-l.webp").exists() or pid not in photos]
    print(f"Optimisation de {len(a_traiter)} photos…")
    for pid, meta in P.optimiser_lot(a_traiter).items():
        photos[pid] = {"alt": photos.get(pid, {}).get("alt", ""), **meta}
    P.sauver(P.FICHIER_PHOTOS, dict(sorted(photos.items())))

    galeries = {nom: list(dict.fromkeys(pid_de(c) for c in lignes(bloc))) for nom, bloc in GALERIES.items()}
    P.sauver(P.FICHIER_GALERIES, galeries)
    print("Import terminé.")


if __name__ == "__main__":
    main()
