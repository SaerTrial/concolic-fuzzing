#!/bin/bash
echo "================================================="
echo " Build AFL+QEMU and full system SymQEMU "
echo "================================================="


echo "[*] Performing basic sanity checks..."

if [ ! "`uname -s`" = "Linux" ]; then

  echo "[-] Error: concolic fuzzing is supported only on Linux."
  exit 1
fi

command -v wget >/dev/null 2>&1 || {
    echo "[-] wget is required but not installed"
    exit 1
}

command -v cargo >/dev/null 2>&1 || {
    echo "[-] curl is required but not installed"
    exit 1
}

if [ ! -f "./AFL++4.34.tar.gz" ]; then
  wget https://github.com/AFLplusplus/AFLplusplus/archive/refs/tags/v4.34c.tar.gz -O AFL++4.34.tar.gz
  tar -xzf AFL++4.34.tar.gz >/dev/null 2>&1
  mv AFLplusplus-4.34c AFLplusplus 
fi

cd "./AFLplusplus"
make 
cd "../"


if [ ! -f "./AFLplusplus/afl-fuzz" ]; then
  echo "[-] Error: afl-fuzz not found!"
  exit 1
fi

if [ ! -f "./AFLplusplus/afl-showmap" ]; then
  echo "[-] Error: afl-showmap not found!"
  exit 1
fi


if [ ! -d "./TriforceQEMU" ]; then
  echo "[-] Error: TriforceQEMU not found!"
  exit 1
fi

if [ ! -d "concolic-replay" ]; then
  echo "[-] Error: concolic-replay not found!"
  exit 1
fi


pip install tomli
echo "[*] Building TriforceQEMU...."

cd "./TriforceQEMU"
mkdir -p build && cd build
../configure                                                    \
    --audio-drv-list=                                           \
    --disable-sdl                                               \
    --disable-gtk                                               \
    --disable-vte                                               \
    --disable-opengl                                            \
    --disable-virglrenderer                                     \
    --disable-werror                                            \
    --target-list=arm-softmmu
ninja

if [ ! -f "./qemu-system-arm" ]; then

  echo "[-] Error: Build qemu-system-arm failed!"
  exit 1

fi


echo "[*] Building concolic executor..."

cd ../../concolic-replay
git submodule update --init --recursive subprojects/symcc-rt
mkdir -p build && cd build
../configure                                                    \
    --audio-drv-list=                                           \
    --disable-sdl                                               \
    --disable-gtk                                               \
    --disable-vte                                               \
    --disable-opengl                                            \
    --disable-virglrenderer                                     \
    --disable-werror                                            \
    --target-list=arm-softmmu
ninja

if [ ! -f "./qemu-system-arm" ]; then

  echo "[-] Error: Build qemu-system-arm failed!"
  exit 1

fi

# top directory
cd "../../"

echo "[*] Installing symcc fuzzing helper that makes use of full system concolic execution"
cargo install --path ./concolic-replay/symcc_fuzzing_helper


echo "[+] Done. Ready for fuzzing..."
