class MockWebDavClient():
    def upload_to(self, *args, **kwargs):
        print('upload_to called')

    def mkdir(self, *args, **kwargs):
        print('mkdir called')

    def download_from(self, *args, **kwargs):
        print('download_from called')
