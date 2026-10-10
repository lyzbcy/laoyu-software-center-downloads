import importlib.util
from pathlib import Path
import unittest
SPEC = importlib.util.spec_from_file_location('collector', Path(__file__).resolve().parents[1]/'scripts/collect.py')
c = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(c)
P = {'id':'app','releaseRepo':'lyzbcy/app','assetName':'app.zip'}
def release(count=8, identifier=1, draft=False):
    return {'draft':draft,'tag_name':'v1','html_url':'https://github.com/lyzbcy/app/releases/tag/v1',
            'assets':[{'id':identifier,'name':'app.zip','download_count':count,'browser_download_url':'https://github.com/lyzbcy/app/releases/download/v1/app.zip'}]}
class CollectorTests(unittest.TestCase):
    def test_brand_migration_counts_both_channels_once_and_uses_new_release(self):
        p={**P,'additionalStatsRepos':['lyzbcy/legacy','lyzbcy/legacy','lyzbcy/app']}
        calls=[]
        def get(path):
            calls.append(path)
            return [release(5 if path.startswith('lyzbcy/legacy/') else 8)] if '?' in path else release(8)
        row=c.collect([p],getter=get)['products'][0]
        self.assertEqual(row['count'],13)
        self.assertEqual(row['repository'],'lyzbcy/app')
        self.assertEqual(sum('legacy/releases?' in call for call in calls),1)
        self.assertEqual(row['latestRelease']['name'],'app.zip')
    def test_stats_only_skills_count_without_desktop_asset_matching(self):
        p={'id':'skills','statsRepo':'lyzbcy/skills'}
        calls=[]
        def get(path): calls.append(path); return [release(72)]
        result=c.collect([p],getter=get)
        self.assertIsNone(result['products'][0]['count'])
        self.assertEqual(result['additionalStats'][0]['count'],72)
        self.assertIsNone(result['additionalStats'][0]['latestRelease'])
        self.assertEqual(len(calls),1)
    def test_stats_only_failure_preserves_prior_extra_row(self):
        p={'id':'skills','statsRepo':'lyzbcy/skills'}
        old=c.collect([p],getter=lambda path:[release(72)])
        def fail(path): raise OSError('offline')
        result=c.collect([p],old,getter=fail)
        self.assertEqual(result['additionalStats'][0]['count'],72)
        self.assertEqual(result['additionalStats'][0]['status'],'stale')
    def test_unknown_and_real_zero_are_distinct(self):
        result=c.collect([P,{'id':'web'}], getter=lambda path: [release(0)] if '?' in path else release(0))
        self.assertEqual(result['products'][0]['count'],0)
        self.assertIsNone(result['products'][1]['count'])
    def test_partial_failure_preserves_previous_timestamp(self):
        old={'products':[{'id':'app','repository':'lyzbcy/app','count':8,'updatedAt':'2026-09-23','latestRelease':None}]}
        def fail(path): raise OSError('offline')
        row=c.collect([P],old,getter=fail)['products'][0]
        self.assertEqual((row['count'],row['updatedAt'],row['status']),(8,'2026-09-23','stale'))
    def test_pagination_and_drafts(self):
        first=[release(1,i) for i in range(100)]
        def get(path): return first if '&page=1' in path else [release(3,101),release(999,102,True)]
        self.assertEqual(len(c.release_list('lyzbcy/app',get)),101)
    def test_duplicate_repository_fetched_once(self):
        calls=[]
        def get(path): calls.append(path); return [release()] if '?' in path else release()
        c.collect([P,{**P,'id':'another'}],getter=get)
        self.assertEqual(sum('?' in call for call in calls),1)
    def test_invalid_counts_do_not_publish_zero(self):
        row=c.collect([P],getter=lambda path:[release(-1)])['products'][0]
        self.assertIsNone(row['count'])
        self.assertEqual(row['status'],'unavailable')
if __name__=='__main__': unittest.main()
