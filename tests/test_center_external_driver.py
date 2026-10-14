import copy,importlib.util,pathlib,unittest
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('center_proof',pathlib.Path(__file__).resolve().parents[1]/'.github/scripts/center-candidate-proof.py');proof=importlib.util.module_from_spec(spec);spec.loader.exec_module(proof)
class DriverBoundaryTests(unittest.TestCase):
 def test_rejects_wrong_mode_name_digest_size_or_extra_fields_before_network(self):
  base={'mode':'installed-update','tag':'center-candidate-20261014-aaaaaaaa','candidates':{'win-x64':{'version':'0.8.12','sha256':'a'*64,'size':1}},'product':{'id':'installed-center-update','oldVersion':'0.8.11','candidate':True},'driver':{'name':'center-installed-update-driver.zip','sha256':'b'*64,'size':6114}}
  changes=[('mode','native-build'),('name','../driver.zip'),('sha256','b'*63),('size',0),('size',1048576),('size',True),('command','anything')]
  for field,value in changes:
   m=copy.deepcopy(base)
   if field=='mode':m['mode']=value
   else:m['driver'][field]=value
   with self.subTest(field=field,value=value),patch.object(proof,'metadata',side_effect=AssertionError('network must not be reached')):
    with self.assertRaisesRegex(ValueError,'external installed driver'):proof.run(m,'win-x64','fake-not-used')
if __name__=='__main__':unittest.main()
