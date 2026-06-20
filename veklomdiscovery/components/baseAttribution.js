import { Attribution } from "ox/erc8021";

export const builderCode = process.env.NEXT_PUBLIC_BASE_BUILDER_CODE || "";

export const dataSuffix = builderCode
  ? Attribution.toDataSuffix({ codes: [builderCode] })
  : undefined;

export const dataSuffixCapability = dataSuffix
  ? {
      dataSuffix: {
        value: dataSuffix,
        optional: true,
      },
    }
  : undefined;
