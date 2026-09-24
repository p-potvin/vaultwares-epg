import os
import tempfile
import unittest
from pathlib import Path

from epg_server import load_dotenv, validate_epg, validate_playlist


class ValidationTest(unittest.TestCase):
    def test_playlist_requires_extm3u_header(self):
        validate_playlist(b'#EXTM3U\n#EXTINF:-1,Test\nhttps://example.test/stream\n')
        with self.assertRaises(ValueError):
            validate_playlist(b'<html>no</html>')

    def test_epg_requires_xmltv_marker(self):
        validate_epg(b'<tv></tv>')
        with self.assertRaises(ValueError):
            validate_epg(b'not xmltv')

    def test_dotenv_does_not_override_existing_process_values(self):
        previous = os.environ.get('EPG_TEST_VALUE')
        os.environ['EPG_TEST_VALUE'] = 'process'
        try:
            with tempfile.TemporaryDirectory() as directory:
                env_file = Path(directory) / '.env'
                env_file.write_text('EPG_TEST_VALUE=file\nEPG_TEST_NEW=value\n', encoding='utf-8')
                load_dotenv(env_file)
            self.assertEqual(os.environ['EPG_TEST_VALUE'], 'process')
            self.assertEqual(os.environ['EPG_TEST_NEW'], 'value')
        finally:
            os.environ.pop('EPG_TEST_NEW', None)
            if previous is None:
                os.environ.pop('EPG_TEST_VALUE', None)
            else:
                os.environ['EPG_TEST_VALUE'] = previous


if __name__ == '__main__':
    unittest.main()
