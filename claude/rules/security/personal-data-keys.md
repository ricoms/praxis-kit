# Personal data as keys

Always-on. Applies to every key.

An email, tax ID or phone number is never a primary, foreign, cache or partition key, or an external ID: it changes, must be erasable, and a key copies it everywhere. Key on an opaque ID and store the personal value as an attribute. A unique constraint on the normalized personal value is allowed.
