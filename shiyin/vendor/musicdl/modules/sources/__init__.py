'''initialize'''
from .bilibili import BilibiliMusicClient
from .bodian import BodianMusicClient
from .fivesing import FiveSingMusicClient
from .kugou import KugouMusicClient
from .kuwo import KuwoMusicClient
from .migu import MiguMusicClient
from .moov import MOOVMusicClient
from .netease import NeteaseMusicClient
from .qianqian import QianqianMusicClient
from .qq import QQMusicClient
from .soda import SodaMusicClient
from .streetvoice import StreetVoiceMusicClient
from .base import BaseMusicClient, BaseMusicClientKwargs
from ..audiobooks import ITunesMusicClient, LRTSMusicClient, LizhiMusicClient, QingtingMusicClient, XimalayaMusicClient
from ..common import GDStudioMusicClient, JBSouMusicClient, MP3JuiceMusicClient, MyFreeMP3MusicClient, TuneHubMusicClient, XiaoBaiMusicClient
from ..thirdpartysites import BuguyyMusicClient, FangpiMusicClient, FiveSongMusicClient, GequbaoMusicClient, GequhaiMusicClient, GequkeMusicClient, HTQYYMusicClient, HeishanMusicClient, KKWSMusicClient, LeedodoMusicClient, MGMP3MusicClient, MituMusicClient, SgogoMusicClient, TwoT58MusicClient, XMFWAVMusicClient, XiagebaMusicClient, YinyuedaoMusicClient, YinyuekuMusicClient
from ..utils import BaseModuleBuilder


'''MusicClientBuilder'''
class MusicClientBuilder(BaseModuleBuilder):
    REGISTERED_MODULES = {
        'BilibiliMusicClient': BilibiliMusicClient,
        'BodianMusicClient': BodianMusicClient,
        'BuguyyMusicClient': BuguyyMusicClient,
        'FangpiMusicClient': FangpiMusicClient,
        'FiveSingMusicClient': FiveSingMusicClient,
        'FiveSongMusicClient': FiveSongMusicClient,
        'GDStudioMusicClient': GDStudioMusicClient,
        'GequbaoMusicClient': GequbaoMusicClient,
        'GequhaiMusicClient': GequhaiMusicClient,
        'GequkeMusicClient': GequkeMusicClient,
        'HeishanMusicClient': HeishanMusicClient,
        'HTQYYMusicClient': HTQYYMusicClient,
        'ITunesMusicClient': ITunesMusicClient,
        'JBSouMusicClient': JBSouMusicClient,
        'KKWSMusicClient': KKWSMusicClient,
        'KugouMusicClient': KugouMusicClient,
        'KuwoMusicClient': KuwoMusicClient,
        'LeedodoMusicClient': LeedodoMusicClient,
        'LizhiMusicClient': LizhiMusicClient,
        'LRTSMusicClient': LRTSMusicClient,
        'MGMP3MusicClient': MGMP3MusicClient,
        'MiguMusicClient': MiguMusicClient,
        'MituMusicClient': MituMusicClient,
        'MOOVMusicClient': MOOVMusicClient,
        'MP3JuiceMusicClient': MP3JuiceMusicClient,
        'MyFreeMP3MusicClient': MyFreeMP3MusicClient,
        'NeteaseMusicClient': NeteaseMusicClient,
        'QianqianMusicClient': QianqianMusicClient,
        'QingtingMusicClient': QingtingMusicClient,
        'QQMusicClient': QQMusicClient,
        'SgogoMusicClient': SgogoMusicClient,
        'SodaMusicClient': SodaMusicClient,
        'StreetVoiceMusicClient': StreetVoiceMusicClient,
        'TuneHubMusicClient': TuneHubMusicClient,
        'TwoT58MusicClient': TwoT58MusicClient,
        'XiagebaMusicClient': XiagebaMusicClient,
        'XiaoBaiMusicClient': XiaoBaiMusicClient,
        'XimalayaMusicClient': XimalayaMusicClient,
        'XMFWAVMusicClient': XMFWAVMusicClient,
        'YinyuedaoMusicClient': YinyuedaoMusicClient,
        'YinyuekuMusicClient': YinyuekuMusicClient,
    }


'''BuildMusicClient'''
BuildMusicClient = MusicClientBuilder().build
