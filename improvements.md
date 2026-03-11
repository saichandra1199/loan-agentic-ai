Confidence scoring → just add confidence: int field to each model
Cross-agent validation → compare bank_output.foir_percentage vs itr_output.gross_income directly in Python — no string parsing
Database persistence → bank_output.model_dump() gives you a dict ready to insert into SQLite
Dashboard → render summary_output.positive_factors and negative_factors as lists directly

