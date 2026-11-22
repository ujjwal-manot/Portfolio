# Builds and flashes the Nucleo-H753ZI 8-bit R-2R DAC firmware with pinned arm-none-eabi-gcc and libopencm3, and runs the Python capture unit tests.
PROJECT = stm32_dac
BUILD_DIR = build
CFILES = main.c
OBJS = $(CFILES:%.c=$(BUILD_DIR)/%.o)
DEVICE = stm32h753zi
ROOT := $(abspath ../..)
OPENCM3_DIR ?= $(ROOT)/third_party/libopencm3
ARM_BIN ?= $(ROOT)/third_party/arm-gnu-toolchain/bin
PREFIX ?= $(ARM_BIN)/arm-none-eabi
OPENOCD ?= openocd
CFLAGS += -Wall -Wextra -Werror -Os -ffunction-sections -fdata-sections
LDFLAGS += --static -nostartfiles -Wl,--gc-sections

include $(OPENCM3_DIR)/mk/genlink-config.mk
include $(OPENCM3_DIR)/mk/gcc-config.mk

LDLIBS += -Wl,--start-group -lc -lgcc -lnosys -Wl,--end-group

.PHONY: all libopencm3 firmware flash test clean

all: libopencm3
	$(MAKE) firmware

libopencm3:
	$(MAKE) -C $(OPENCM3_DIR) TARGETS=stm32/h7 PREFIX=$(PREFIX)-

firmware: $(BUILD_DIR)/$(PROJECT).elf $(BUILD_DIR)/$(PROJECT).bin

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/%.o: %.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) $(CPPFLAGS) $(ARCH_FLAGS) -o $@ -c $<

$(BUILD_DIR)/$(PROJECT).elf: $(OBJS) $(LDSCRIPT) | $(BUILD_DIR)

flash: all
	$(OPENOCD) -f board/st_nucleo_h743zi.cfg -c "program $(BUILD_DIR)/$(PROJECT).elf verify reset exit"

test:
	pytest -q test_capture.py

clean:
	rm -rf $(BUILD_DIR) generated.$(DEVICE).ld

include $(OPENCM3_DIR)/mk/genlink-rules.mk
include $(OPENCM3_DIR)/mk/gcc-rules.mk
