# LQ-2241 sdist source byte-comparison gate

- The normalized archive is read without filesystem extraction.
- Each file is addressed below the bound sdist root.
- Generated metadata presence is checked before source comparison.
- Remaining archive names must equal enumerated source names exactly.
- Every source payload then compares byte-for-byte.
- Distribution and late sdist phases repeat the same binding.
- The retained source-file count must remain unchanged across phases.
