ARCH := amd64

# CPU arch
ifeq ($(ARCH),amd64)
	QEMU :=
endif

ifeq ($(ARCH),i386)
	CXX := i686-linux-gnu-g++
	QEMU := qemu-i386-static
endif

ifeq ($(ARCH),arm)
	CXX := arm-linux-gnueabihf-g++
	QEMU := qemu-arm-static
endif

ifeq ($(ARCH),arm64)
	CXX := aarch64-linux-gnu-g++
	QEMU := qemu-aarch64-static
endif

# build option
CXX_FLAGS := $(CXX_FLAGS) -std=c++14 -fvisibility=hidden -fvisibility-inlines-hidden

# build option by OS
ifeq ($(shell uname),Linux)
	CXX_FLAGS := $(CXX_FLAGS) -DWEBRTC_LINUX=1 -DWEBRTC_POSIX=1
	OS := linux
else
	CXX_FLAGS := $(CXX_FLAGS) -DWEBRTC_MAC=1 -DWEBRTC_POSIX=1
	OS := macos
endif

# headers
LIBWEBRTC_PATH := ../opt/$(OS)_$(ARCH)
CXX_FLAGS := $(CXX_FLAGS) -I $(LIBWEBRTC_PATH)/include
CXX_FLAGS := $(CXX_FLAGS) -I $(LIBWEBRTC_PATH)/include/third_party/abseil-cpp

# linker option
LD_FLAGS := $(LD_FLAGS) -L $(LIBWEBRTC_PATH)/lib -lwebrtc -lpthread

default: test

test-$(ARCH): main.cpp
	$(CXX) $(CXX_FLAGS) -o main-$(ARCH).o -c $^
	$(CXX) main-$(ARCH).o $(LD_FLAGS) -o $@

run: test-$(ARCH)
	$(QEMU) ./test-$(ARCH)

clean:
	$(RM) test-* main-*

.PHONY: clean