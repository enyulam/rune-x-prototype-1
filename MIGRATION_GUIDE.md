# Database Migration Guide for Rune-X

After rebranding to Rune-X, the database schema has been enhanced with new features. **Note:** OCR/processing endpoints are temporarily disabled during the Chinese-handwriting refactor; migrations still apply for uploads/history/exports.

## Quick Migration

Run the following command to sync the Prisma schema with your database:

```bash
npm run db:push
```

This will:
- Add new fields to the `Upload` model (provenance, imagingMethod, scriptType, metadata)
- Add new fields to the `GlyphMatch` model (strokeCount, contourComplexity, isReconstructed)
- Create new models: `ReconstructionVersion` and `Export`
- Add new enum: `ExportFormat`

## If Migration Fails

If you encounter errors during migration:

1. **Backup your database first:**
   ```bash
   cp prisma/db/dev.db prisma/db/dev.db.backup
   ```

2. **Reset the database (WARNING: This deletes all data):**
   ```bash
   npm run db:reset
   ```

3. **Or manually migrate using Prisma Migrate:**
   ```bash
   npm run db:migrate
   ```

## Verify Migration

After running `npm run db:push`, verify the migration was successful by checking:

1. The database file should be updated
2. No errors in the console when starting the app
3. Upload functionality should work

## New Features Enabled After Migration

- ✅ Enhanced metadata tracking (provenance, imaging method)
- ✅ Glyph reconstruction tracking (isReconstructed flag)
- ✅ Version control for reconstructions
- ✅ Export history tracking
- ✅ Support for multiple export formats

## Troubleshooting

### Error: "Unknown column 'provenance'"

This means the database hasn't been migrated. Run:
```bash
npm run db:push
```

### Error: "SQLITE_ERROR: no such table: ReconstructionVersion"

The new tables haven't been created. Run:
```bash
npm run db:push
```

### Error: "Cannot find module '@prisma/client'"

Regenerate the Prisma client:
```bash
npm run db:generate
```





