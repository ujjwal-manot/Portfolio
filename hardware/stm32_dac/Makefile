# Builds and flashes the Nucleo-H753ZI 8-bit R-2R DAC firmware with pinned arm-none-eabi-gcc and libopencm3, and runs the Python capture unit tests.
PROJECT = stm32_dac
BUILD_DIR = build
CFILES = main.c
DEVICE = stm32h753zi
OPENCM3_DIR ?= ../../third_party/libopencm3
ARM_BIN ?= ../../third_party/arm-gnu-toolchain/bin
PREFIX ?= $(ARM_BIN)/arm-none-eabi-
OPENOCD ?= openocd
CFLAGS += -Wall -Wextra -Werror -Os -ffunction-sections -fdata-sections
LDFLAGS += -Wl,--gc-sections

include $(OPENCM3_DIR)/mk/genlink-config.mk
include $(OPENCM3_DIR)/mk/gcc-config.mk

.PHONY: all libopencm3 flash test clean

all: $(BUILD_DIR)/$(PROJECT).elf $(BUILD_DIR)/$(PROJECT).bin

libopencm3:
	$(MAKE) -C $(OPENCM3_DIR) TARGETS=stm32/h7 PREFIX=$(PREFIX)

$(BUILD_DIR)/$(PROJECT).elf: libopencm3

flash: $(BUILD_DIR)/$(PROJECT).elf
	$(OPENOCD) -f board/st_nucleo_h743zi.cfg -c "program $(BUILD_DIR)/$(PROJECT).elf verify reset exit"

test:
	pytest -q test_capture.py

clean:
	rm -rf $(BUILD_DIR) generated.$(DEVICE).ld

include $(OPENCM3_DIR)/mk/genlink-rules.mk
include $(OPENCM3_DIR)/mk/gcc-rules.mk
