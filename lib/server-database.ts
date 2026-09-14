import postgres from "postgres";

let database: ReturnType<typeof postgres> | null = null;

export function getDatabase() {
  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) return null;
  database ??= postgres(databaseUrl, {
    max: 1,
    prepare: false,
    ssl: "require",
    connect_timeout: 12,
    idle_timeout: 5,
  });
  return database;
}
