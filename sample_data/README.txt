SAMPLE DATA
===========
This directory contains anonymized sample documents for testing.
Real user data should go in user_data/ (which is gitignored).

To test the system:
  1. Copy sample documents here
  2. Set COS_DATA_DIR=sample_data in .env (or use --dir flag)
  3. Run: cos index --dir sample_data
  4. Run: cos query "what deadlines do I have?"
