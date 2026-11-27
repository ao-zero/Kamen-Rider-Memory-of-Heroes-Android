# Kamen Rider: Memory of Heroes — Android ARM64 Port (`nixport` Edition)

<p align="center">
  <img src="assets/hero_banner.png" alt="Kamen Rider Memory of Heroes Android ARM64 Banner" width="100%" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Android%20ARM64%20(aarch64)-3DDC84?style=for-the-badge&logo=android&logoColor=white" alt="Android ARM64" />
  <img src="https://img.shields.io/badge/Host-nixport%20(nixport.port.v1)-3B66F5?style=for-the-badge" alt="nixport" />
  <img src="https://img.shields.io/badge/Render%20API-Vulkan%201.3%20(Turnip)-E01E37?style=for-the-badge&logo=vulkan&logoColor=white" alt="Vulkan 1.3" />
  <img src="https://img.shields.io/badge/Subtitle-Patch%20Indo%205%2C993%20Baris-22C55E?style=for-the-badge" alt="Patch Indo" />
  <img src="https://img.shields.io/badge/License-GPL--2.0-blue?style=for-the-badge" alt="License" />
</p>

> **Edisi Proyek Kamen Rider: Memory of Heroes (AO Zero & Bakka Sub):**
> - **PC Native Edition (Windows x64):** https://github.com/ao-zero/Kamen-Rider-Memory-of-Heroes-PC
> - **Android ARM64 Port (`nixport` Edition — Repo Ini):** https://github.com/ao-zero/Kamen-Rider-Memory-of-Heroes-Android

---

## Edisi Tersedia (PC & Android)

| Platform | Repository | Keterangan |
| :--- | :--- | :--- |
| **Android ARM64 (`nixport`)** | [ao-zero/Kamen-Rider-Memory-of-Heroes-Android](https://github.com/ao-zero/Kamen-Rider-Memory-of-Heroes-Android) *(Repo Ini)* | Port Android ARM64 (`FEXCore` + `shadPS4`) |
| **Windows PC (x64)** | [ao-zero/Kamen-Rider-Memory-of-Heroes-PC](https://github.com/ao-zero/Kamen-Rider-Memory-of-Heroes-PC) | Versi PC Native (`v1.2.0`, 60 FPS, Clean UI) |

---

## Ringkasan Proyek

**Kamen Rider: Memory of Heroes — Android ARM64 Port (`nixport` Edition)** adalah proyek port dan launcher *open-source* untuk menjalankan **Kamen Rider: Memory of Heroes (`CUSA17374`)** di perangkat Android ARM64 menggunakan arsitektur **`nixport` + `FEXCore` (guest x86-64 → ARM64) + `shadPS4` Vulkan 1.3**, lengkap dengan **Built-in Patch Bahasa Indonesia (5.993 baris gaya fansub Bakka Sub)** dan **Touch Virtual Gamepad** bawaan.

Dibangun khusus untuk tiga Rider utama:
- **Kamen Rider Double (W)** — Cyclone & Joker
- **Kamen Rider OOO** — TaToBa (Taka, Tora, Batta)
- **Kamen Rider Zero-One** — Rising Hopper

### Tim & Partner
- **Port Lead & Developer:** **AO Zero**
- **Community Partner & Lokalisasi Bahasa Indonesia:** [**Bakka Sub**](https://www.bakkasub.my.id)

---

## Fitur Utama

- **Clean UI Launcher v1.0.0 (Dark & Light Mode):** Antarmuka bersih bergaya desktop/mobile yang terinspirasi [XSEmu](https://github.com/zortos293/xsemu), otomatis menyesuaikan skala sentuh (+25% & fullscreen) saat dijalankan di HP Android melalui `nixport`.
- **Built-in Patch Bahasa Indonesia (Bakka Sub x AO Zero):**
  - 1-klik aktifkan **5.993 baris terjemahan** Bahasa Indonesia (`help_list`, `menu_text`, `mission_talk`, `name_text`) pada `CUSA17374/Media/sharedassets0.assets`.
  - Pure-Python Unity `2017.4.40f1` patcher (0 dependensi eksternal) dengan **backup vanilla otomatis** di `home/kr_moh/bin/user/vanilla_backup/` sehingga bisa dikembalikan ke **Original (EN/JP)** kapan saja.
- **Preset Performa Mobile (`540p / 720p / 1080p` & `30 / 60 FPS`):**
  - Sinkronisasi otomatis `vblank_frequency` (`60 Hz` = 30 FPS Locked, `120 Hz` = 60 FPS Native Unlock), `Mailbox`, `async_shader_compilation`, `FSR + RCAS`, dan `pipeline_cache_enabled`.
  - Proteksi anti-bentrok input: otomatis menonaktifkan `mouse_to_joystick` saat `FEXDROID_PRESENT` aktif agar kamera analog sentuh/gamepad mulus.
- **Touch Virtual Gamepad Siap Pakai (`virtualkeys.json`):** Layout landscape khusus gameplay Kamen Rider (Form Change `L2`, Guard/Lock-On `L1`, Rider Power `R1`, Finisher `R2`, diamond `△○×□`, Dual Analog, D-Pad, Map, Options) otomatis terpasang saat import paket ke `nixport`.
- **Savegame Manager & 50 Trophy Bilingual:** Backup/restore save `.zip` portabel di storage `home/kr_moh/` serta katalog 50 trophy PS4 resmi (Bahasa Indonesia & English).
- **Integrasi Kontrak `nixport.port.v1` Penuh:** Mendukung verb protocol `launcher | game | info | config | check` termasuk skema konfigurasi dinamis (`entry_main.py`).

---

## Spesifikasi Perangkat Android

| Komponen | Minimum (`540p` · `30 FPS`) | Rekomendasi (`720p` · `60 FPS`) |
| :--- | :--- | :--- |
| **OS** | Android 11+ (ARM64 / `aarch64`) | Android 13 / 14 / 15 (ARM64) |
| **Chipset / GPU** | Qualcomm Snapdragon 8 Gen 1 / 7+ Gen 2 (Adreno 7xx) | Qualcomm Snapdragon 8 Gen 2 / 8 Gen 3 / 8 Elite (Adreno 740+) |
| **Driver Vulkan** | Vulkan 1.3 via **Mesa Turnip** (diatur di `nixport`) | Mesa Turnip terbaru (Vulkan 1.3 / 1.4) |
| **RAM** | 8 GB | 12 GB atau 16 GB |
| **Penyimpanan Kosong** | 15 GB (internal storage cepat / UFS 3.1+) | 20 GB+ (UFS 4.0) |
| **Kontrol** | Layar Sentuh (`virtualkeys.json` bawaan) | Gamepad Bluetooth / USB-C (DualSense, Xbox, Backbone, Gamesir) |

> **Catatan GPU:** Chipset non-Snapdragon (Mali / Xclipse / PowerVR) saat ini belum direkomendasikan karena `shadPS4` Vulkan backend membutuhkan fitur Vulkan 1.3 lengkap yang saat ini paling matang di driver **Adreno Turnip**.

---

## Tutorial Instalasi Step-by-Step (Android)

> **Penting (Legal):** Repository dan file rilis ini **TIDAK** menyertakan file game, ROM, atau `eboot.bin` berhak cipta. Anda harus menggunakan dump legal dari game PS4 *Kamen Rider: Memory of Heroes* (`CUSA17374`) milik Anda sendiri.

### Langkah 1 — Install Aplikasi Host `nixport`
1. Unduh APK terbaru **`nixport`** dari repositori resmi [zFitness/nixport](https://github.com/zFitness/nixport/releases).
2. Pasang APK `nixport` di perangkat Android Anda dan berikan izin akses penyimpanan (*All Files Access*) agar bisa membaca folder dump game di `/sdcard/`.
3. Buka `nixport`, pastikan rootfs Linux ARM64 dan driver Vulkan **Turnip** sudah terpasang di menu pengaturan `nixport`.

### Langkah 2 — Unduh & Import Paket Port (`KamenRiderMoH.nixport.1.0.0.zip`)
1. Unduh **`KamenRiderMoH.nixport.1.0.0.zip`** dari halaman [Releases](https://github.com/ao-zero/Kamen-Rider-Memory-of-Heroes-Android/releases).
2. Buka aplikasi **`nixport`** → masuk ke tab **Library** → pilih **Import Port package**.
3. Pilih file `KamenRiderMoH.nixport.1.0.0.zip`.
4. `nixport` akan otomatis membaca `port.json`, mengekstrak `KamenRiderMoH-arm64.AppImage`, dan mendaftarkan tata letak tombol sentuh `virtualkeys.json`.

### Langkah 3 — Siapkan Folder Dump Game (`CUSA17374`) di Penyimpanan Internal
Salin folder dump game PS4 Anda (disarankan sudah termasuk **Update v1.01**) ke penyimpanan internal Android, misalnya:
```text
/storage/emulated/0/Games/CUSA17374/
├── eboot.bin                  <-- Wajib ada!
├── sce_sys/
│   └── param.sfo
└── Media/
    └── sharedassets0.assets   <-- Target Patch Bahasa Indonesia
```
> Hindari meletakkan dump game di SD Card eksternal (FAT32/exFAT lambat) karena akan memicu stutter saat streaming aset Unity.

### Langkah 4 — Konfigurasi & Aktifkan Patch Bahasa Indonesia
1. Di dalam `nixport`, tap kartu **Kamen Rider: Memory of Heroes** → pilih **KR Memory of Heroes Launcher**.
2. Di tab **Overview**, klik **Change** pada baris *Folder* lalu arahkan ke `/storage/emulated/0/Games/CUSA17374`.
   - Status game akan otomatis berubah menjadi hijau (**Ready**) beserta versi game (mis. `v01.01`).
3. Atur **Quick Overrides** sesuai performa HP Anda:
   - **Snapdragon 8 Gen 1 / 7+ Gen 2:** `540p` + `30 FPS` (atau `60 FPS`) + FSR `On`.
   - **Snapdragon 8 Gen 2 / 8 Gen 3 / 8 Elite:** `720p` + `60 FPS`.
4. Untuk mengaktifkan **Subtitle Bahasa Indonesia (Bakka Sub)**:
   - Klik tombol **Patch Indo** di bar atas, atau buka tab **Patch Indo** → klik **Apply Patch Indonesia**.
   - Tunggu beberapa detik hingga log menampilkan `5,993` entri sukses diterapkan. File original Anda otomatis dicadangkan di `home/kr_moh/bin/user/vanilla_backup/`.
5. Tekan tombol biru **Play** untuk memulai permainan!

---

## Layout Kontrol Sentuh & Gamepad (`virtualkeys.json`)

Tata letak sentuh landscape bawaan sudah dioptimalkan agar jempol dan jari telunjuk tidak saling bertabrakan saat bertarung:

| Tombol / Stick | Posisi Layar (Landscape) | Fungsi dalam Game |
| :--- | :--- | :--- |
| **Left Analog Stick** | Kiri Bawah | Menggerakkan Kamen Rider |
| **D-Pad** | Kiri Tengah-Bawah | Ganti Item / Aksi Menu / Shortcut |
| **Right Analog Stick** | Kanan Bawah-Tengah | Kontrol Kamera 360° |
| **`□` (Square)** | Kanan Bawah (Kiri Diamond) | Light Attack / Serangan Cepat |
| **`△` (Triangle)** | Kanan Bawah (Atas Diamond) | Heavy Attack / Form Skill |
| **`○` (Circle)** | Kanan Bawah (Kanan Diamond) | Dodge / Dash / Cancel |
| **`×` (Cross)** | Kanan Bawah (Bawah Diamond) | Jump / Confirm |
| **`L1`** | Kiri Atas-Bawah | Guard / Lock-On Target |
| **`L2`** | Kiri Atas | Form Change (W / OOO / Zero-One) |
| **`R1`** | Kanan Atas-Bawah | Rider Power Stance |
| **`R2`** | Kanan Atas | Finisher / Max Drive |
| **`MAP` (Select / Touchpad)** | Tengah Atas Kiri | Peta / Objective |
| **`OPTIONS` (Start)** | Tengah Atas Kanan | Menu Pause |

> Anda juga dapat menyambungkan **Gamepad Bluetooth / USB-C** (DualShock 4, DualSense, Xbox Controller, GameSir, Backbone) secara langsung dan menyembunyikan overlay tombol sentuh dari menu cepat `nixport`.

---

## Struktur Proyek

```text
Kamen-Rider-Memory-of-Heroes-Android/
├── .github/workflows/
│   └── arm64-port.yml                # GitHub Actions CI: cross-build & rilis .nixport.<ver>.zip
├── assets/                           # Icon, banner, logo Bakka Sub, 50 icon trophy
├── launcher/
│   └── kr_android_launcher.py        # Launcher Clean UI v1.0.0 (Pure Python Tkinter, Dark/Light)
├── packaging/arm-linux/
│   ├── port.json                     # Manifest kontrak nixport.port.v1
│   ├── virtualkeys.json              # Layout tombol sentuh landscape nixport.virtualkeys.v1
│   ├── AppRun                        # Entrypoint AppImage
│   ├── entry.sh                      # Handler verb protocol (launcher|game|info|config|check)
│   ├── entry_main.py                 # JSON schema/get/set dinamis untuk kartu nixport
│   ├── build-runtime.sh              # Fase 4: Cross-compile shadPS4 ARM64 + FEXCore (Debian Trixie)
│   ├── ci-deps.sh                    # Setup dependency cross-compile Ubuntu 24.04
│   ├── cross-toolchain.cmake         # Toolchain Clang + LLD + aarch64-linux-gnu
│   ├── fetch-sysroot.py              # Pengunduh Debian Trixie arm64 sysroot + Vulkan-Headers
│   └── build.sh                      # Bundler Type-2 ARM64 AppImage & KamenRiderMoH.nixport.<ver>.zip
├── runtime/
│   └── runtime-lock.json             # Pin sumber open-source shadps4-arm64 + FEXCore (GPL-2.0)
├── patches/
│   └── id_patch.json                 # 5.993 baris terjemahan Bahasa Indonesia (Bakka Sub)
├── scripts/
│   ├── android_config.py             # Storage $HOME/kr_moh, sync config.json & input_config
│   ├── indo_patcher.py               # Pure-Python Unity 2017.4 SerializedFile patcher
│   ├── save_manager.py               # Backup & restore save CUSA17374 (lintas-platform)
│   ├── sfo_parser.py                 # Binary parser param.sfo
│   └── trophy_manager.py             # Katalog 50 trophy bilingual
├── LICENSE                           # GPL-2.0-or-later
└── README.md                         # Dokumentasi & panduan instalasi ini
```

---

## Build dari Source & GitHub Actions CI

### Uji Launcher Secara Lokal (Windows / Linux Desktop)
```bash
git clone https://github.com/ao-zero/Kamen-Rider-Memory-of-Heroes-Android.git
cd Kamen-Rider-Memory-of-Heroes-Android
python3 launcher/kr_android_launcher.py
```

### Build Paket `nixport` di Linux (Ubuntu 24.04)
```bash
# 1. Pasang toolchain cross-compile (Clang, LLD, CMake, Ninja, VMA, Vulkan-Headers)
bash packaging/arm-linux/ci-deps.sh

# 2. Ambil host packaging script dari zFitness/nixport
mkdir -p fexdroid
curl -fsSL https://codeload.github.com/zFitness/nixport/tar.gz/refs/heads/main \
  | tar xz -C fexdroid --strip-components=1
chmod +x fexdroid/scripts/*.sh

# 3. Build & kemas paket nixport (.AppImage + .zip)
KR_HOST_TOOLS="$PWD/fexdroid" bash packaging/arm-linux/build.sh
```
Hasil akhir berada di `packaging/arm-linux/dist/kamen-rider-moh-port.zip`.  
Pada **GitHub Actions**, push tag `v*` (mis. `v1.0.0`) atau jalankan workflow **ARM64 port package** secara manual untuk menghasilkan `KamenRiderMoH.nixport.<ver>.zip` + `.sha256` secara otomatis.

---

## Troubleshooting & FAQ

- **`eboot.bin` tidak ditemukan saat memilih folder:** Pastikan Anda memilih folder `CUSA17374` yang langsung berisi `eboot.bin` dan folder `sce_sys/` (bukan file `.pkg` mentah — file `.pkg` harus diekstrak/dump terlebih dahulu).
- **Stutter atau patah-patah di menit pertama bermain:** Normal saat pertama kali memasuki area baru karena GPU menyusun shader pipeline. Setelah tersimpan di `pipeline_cache`, sesi berikutnya akan jauh lebih mulus. Jika terjadi artefak grafis setelah update driver Turnip, gunakan tombol **Clear cache** di tab **Overview**.
- **Layar hitam saat masuk game:** Pastikan Anda menggunakan driver **Mesa Turnip** (bukan driver sistem bawaan vendor) di pengaturan `nixport`, dan coba turunkan resolusi ke `540p` + `30 FPS`. Cek log detail di `home/kr_moh/logs/launch.log`.
- **Ingin kembali ke teks English/Japanese original:** Buka tab **Patch Indo** → klik **Restore Original (EN/JP)**. File `sharedassets0.assets` akan dikembalikan 100% utuh dari backup vanilla.

---

## Credits & Acknowledgments

- **[AO Zero](https://github.com/ao-zero)** — Port Lead & Developer *Kamen Rider: Memory of Heroes* (PC Native & Android ARM64 Editions).
- **[Bakka Sub](https://www.bakkasub.my.id)** — Community Partner & tim fansub lokalisasi Bahasa Indonesia (5.993 baris).
- **[zFitness/nixport](https://github.com/zFitness/nixport)** & **[zFitness/gow3_android](https://github.com/zFitness/gow3_android)** — Host runtime ARM64 Android non-root, kontrak `nixport.port.v1` / `nixport.virtualkeys.v1`, dan referensi arsitektur cross-compile `FEXCore` + `shadPS4`.
- **[XSEmu](https://github.com/zortos293/xsemu)** *(by zortos293 · GPL-2.0)* — Inspirasi desain antarmuka Clean UI (hero detail, 2×2 hairline spec grid, segmented Quick Overrides).
- **[shadPS4](https://github.com/shadps4-emu/shadPS4)** & **[FEX-Emu / FEXCore](https://github.com/FEX-Emu/FEX)** — Engine emulasi Vulkan 1.3 PS4 dan translasi JIT x86-64 → ARM64.

---

## Legal Disclaimer

- *Kamen Rider: Memory of Heroes* adalah merek dagang dan hak cipta milik **BANDAI NAMCO Entertainment Inc.**, **ISHIMORI PRODUCTION INC.**, dan **TOEI COMPANY, LTD.**
- Proyek ini adalah utilitas launcher dan port non-komersial buatan penggemar untuk tujuan preservasi dan interoperabilitas.
- **TIDAK ADA** binary game, aset berhak cipta, audio, video, atau ROM yang didistribusikan dalam repositori ini. Pengguna wajib memiliki salinan legal game dari konsol PlayStation 4 pribadi.
