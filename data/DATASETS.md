# Dataset manifest

The repository deliberately includes the full Phase 1 and Phase 2 datasets.
All hashes use SHA-256.

| File | Purpose | Size (bytes) | SHA-256 |
|---|---|---:|---|
| `raw/jena_climate_2009_2016.xlsx` | Original source workbook | 35,463,444 | `dabd7c01f3ab99b72d6e9eefb0f73b8796f04696bbae6917cf22ef8e8a6ce231` |
| `processed/observations.csv` | Canonical Phase 1 observations in interchange format | 55,597,689 | `44a68d0d152f4d4ae6bf835b3c9220343e84066621e3d49daee01d3347c4647e` |
| `processed/observations.parquet` | Canonical Phase 1 training source | 7,594,068 | `e2fdbbec38a201dfcd016acc8683b58d7f252b00fa364d448fcdd686abe86e36` |
| `processed/labelled_train.csv` | Chronological Phase 2 labelled training set | 62,243,036 | `3ddd6e1473bb1ea60abec452a3b4aa3a4c65a6e8482fb48fd90b0f15a52e62ad` |
| `processed/labelled_test.csv` | Chronological Phase 2 labelled test set | 15,607,532 | `05dcf659ea937a2cc92ae9b0d1325d6ec5701d5870490205214ba28085d45c38` |

The source workbook is copied byte-for-byte from the user-supplied local file.
Consumers are responsible for confirming that their use and redistribution of the
underlying Jena climate data complies with the original dataset terms.
