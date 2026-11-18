"""Native seating slots: preview, exact recheck, parenting and payment failures."""
import types,sys,unittest
from unittest.mock import patch
import test_placement as env
import tyjokr_a11y_chair_snap as snap
import tyjokr_a11y_grid as grid
import tyjokr_a11y_layers as layers
import tyjokr_a11y_tiles as tiles
import tyjokr_a11y_settings as settings
import tyjokr_a11y_scanner as scanner

Q=lambda:types.SimpleNamespace(x=0.,y=0.,z=0.,w=1.)
class Seat:
 def __init__(self,owner,ident=100,position=None):
  self.owner=owner;self.slot_name_hash=ident;self.position=position or env.Vec(3.5,0,3.5)
  self.transform=types.SimpleNamespace(orientation=Q());self.is_enabled=True;self.occupied=False
  self.valid=True;self.deco=False;self.calls=[];self.fail_parent=False;self.wrong_hash=False
 @property
 def children(self):return [o for o in env.world.objects.values() if getattr(o,'parent',None) is self.owner and getattr(getattr(o,'location',None),'slot_hash',None)==self.slot_name_hash]
 @property
 def empty(self):return not self.occupied and not self.children
 def is_deco_slot(self):return self.deco
 def is_valid_for_placement(self,*,obj=None,definition=None):
  self.calls.append(('object' if obj is not None else 'definition',obj or definition));return self.valid
 def add_child(self,obj):
  obj.parent=types.SimpleNamespace(is_part=False) if self.fail_parent else self.owner
  obj.location=types.SimpleNamespace(slot_hash=999 if self.wrong_hash else self.slot_name_hash,joint_name_hash=None)
  obj.position=self.position;obj.orientation=self.transform.orientation

class Tests(unittest.TestCase):
 setUp_base=env.PlacementTests.setUp
 choose=env.PlacementTests.choose;ack=env.PlacementTests.ack;serial=env.PlacementTests.serial;said=env.PlacementTests.said
 def setUp(self):
  self.setUp_base();env.place._pending.update(chair_request=None,surface_id=None)
  env.world.definitions[501].get_tags=lambda:['BuyCatSSDiningChair']
  definition=env.Definition(700,100);definition.get_tags=lambda:['BuyCatSSDiningTable']
  self.table=env.Obj(77,definition,position=env.Vec(3.5,0,4.5));self.table.orientation=Q();self.table.owner=env.world.household
  self.part=types.SimpleNamespace(is_part=True,part_owner=self.table,part_group_index=0)
  self.seat=Seat(self.part);self.table.slots=[self.seat];env.world.objects[77]=self.table
  self.focus=self.table;self.locations={(3,4):[self.table]}
  self.frame=types.SimpleNamespace(inside=lambda i,j:True,tile_of=lambda x,z:(int(x),int(z)))
  self.patches=[patch.dict(sys.modules,tag=types.SimpleNamespace(Tag=lambda value:types.SimpleNamespace(name=value))),
   patch.object(grid,'_tile',(3,3)),patch.object(grid,'_level',0),patch.object(grid,'_facing',0),
   patch.object(grid,'cursor',lambda:(env.Vec(grid._tile[0]+.5,0,grid._tile[1]+.5),0,'id')),
   patch.object(grid,'_surface',lambda:'surface'),patch.object(grid,'_name',lambda obj:'Native table name'),
   patch.object(layers,'focused_target',lambda:self.focus),
   patch.object(tiles,'frame',lambda:self.frame),
   patch.object(tiles,'position',lambda f,i,j,l:env.Vec(i+.5,0,j+.5)),
   patch.object(tiles,'objects_on',lambda f,i,j,l:self.locations.get((i,j),[])),
   patch.object(tiles,'relative',lambda di,dj:'relative {}, {}'.format(di,dj)),
   patch.object(scanner,'_speak_parts',lambda parts:self.parts.append(''.join(str(x) for x in parts))),
   patch.object(settings,'get',lambda key,default=None:default)]
  for p in self.patches:p.start();self.addCleanup(p.stop)
  self.choose(name='Dining chair')
 def request(self):return snap.try_place(env.place.product(),self.frame)
 def test_native_part_seat_sets_rotation_and_uses_original_payment_transaction(self):
  self.assertTrue(grid._build_place());self.assertTrue(self.ack())
  obj=env.world.objects[env.place._last['obj_id']]
  self.assertIs(obj.parent,self.part);self.assertIs(obj.orientation,self.seat.transform.orientation)
  self.assertEqual(obj.moves,[]);self.assertEqual(env.world.funds.money,700)
  self.assertEqual([c[0] for c in self.seat.calls],['definition','object'])
  self.assertTrue(self.said('Native table name'))
 def test_occupied_seat_refuses_without_creating_or_buying(self):
  self.seat.occupied=True;self.assertFalse(self.request());self.assertEqual(set(env.world.objects),{77});self.assertEqual(env.world.funds.money,1000)
 def test_native_definition_refusal_is_authoritative(self):
  self.seat.valid=False;self.assertFalse(self.request());self.assertEqual(env.world.funds.money,1000)
 def test_disabled_and_decorative_slots_are_not_seats(self):
  for attribute in ['is_enabled','deco']:
   self.seat.is_enabled=True;self.seat.deco=False;setattr(self.seat,attribute,False if attribute=='is_enabled' else True)
   self.assertFalse(self.request())
 def test_same_seat_must_still_be_available_at_acknowledgement(self):
  other=Seat(self.part,101,env.Vec(4.5,0,4.5));self.table.slots.append(other)
  self.assertTrue(self.request());self.seat.occupied=True;self.assertFalse(self.ack())
  self.assertEqual(env.world.funds.money,1000);self.assertEqual(other.calls,[])
 def test_table_moved_before_acknowledgement_refuses(self):
  self.assertTrue(self.request());self.table.position=env.Vec(9,0,9)
  self.assertFalse(self.ack());self.assertEqual(env.world.funds.money,1000)
 def test_seat_transform_changed_before_acknowledgement_refuses(self):
  self.assertTrue(self.request());self.seat.position=env.Vec(4.5,0,3.5)
  self.assertFalse(self.ack());self.assertEqual(env.world.funds.money,1000)
 def test_focus_or_cursor_change_refuses(self):
  self.assertTrue(self.request());self.focus=None
  self.assertFalse(self.ack());self.assertEqual(env.world.funds.money,1000)
 def test_actual_object_can_be_refused_after_a_valid_preview(self):
  self.assertTrue(self.request());self.seat.valid=False
  self.assertFalse(self.ack());self.assertEqual(env.world.funds.money,1000);self.assertEqual(set(env.world.objects),{77})
 def test_wrong_parent_is_rejected_before_payment(self):
  self.seat.fail_parent=True;self.assertTrue(self.request());self.assertFalse(self.ack());self.assertEqual(env.world.funds.money,1000)
 def test_wrong_slot_hash_is_rejected_before_payment(self):
  self.seat.wrong_hash=True;self.assertTrue(self.request());self.assertFalse(self.ack());self.assertEqual(env.world.funds.money,1000)
 def test_registration_must_preserve_the_native_attachment(self):
  self.assertTrue(self.request())
  def register(obj):obj.parent=None;return True
  with patch.object(env.place,'_register',register):self.assertFalse(self.ack())
  self.assertEqual(env.world.funds.money,1000)
 def test_failed_payment_removes_the_chair_and_frees_the_seat(self):
  env.world.funds.fail_remove='refuse';self.assertTrue(self.request());self.assertFalse(self.ack())
  self.assertEqual(env.world.funds.money,1000);self.assertTrue(self.seat.empty)
 def test_native_part_slot_is_preferred_over_its_root_duplicate(self):
  root_slot=Seat(self.table,100);self.table.slots=[root_slot,self.seat]
  self.assertTrue(self.request());self.assertTrue(self.ack());self.assertEqual(root_slot.calls,[])
 def test_nearby_table_can_snap_without_focusing_it(self):
  self.focus=None;self.assertTrue(self.request());self.assertTrue(self.ack())
 def test_facing_away_keeps_ordinary_floor_placement(self):
  self.focus=None;grid._facing=2;self.assertIsNone(self.request());self.assertEqual(env.place._pending['serial'],0)
 def test_equally_near_tables_require_explicit_focus(self):
  self.focus=None;other=env.Obj(78,self.table.definition);other.orientation=Q();self.locations={(2,4):[self.table],(4,4):[other]}
  self.assertFalse(self.request());self.assertEqual(env.place._pending['serial'],0)
 def test_unrelated_objects_and_disabled_setting_delegate_unchanged(self):
  env.world.definitions[501].get_tags=lambda:[];self.assertIsNone(self.request())
  env.world.definitions[501].get_tags=lambda:['BuyCatSSDiningChair']
  with patch.object(settings,'get',lambda key,default=None:False if key=='chair_snapping' else default):self.assertIsNone(self.request())
 def test_desk_chair_matches_a_desk(self):
  env.world.definitions[501].get_tags=lambda:['BuyCatSSDeskChair'];self.table.definition.get_tags=lambda:['BuyCatSSDesk']
  self.assertTrue(self.request());self.assertTrue(self.ack())
 def test_native_config_can_disable_snapping_independently(self):
  self.assertEqual(settings._FILE_MAP[('build cursor','chair snapping')],'chair_snapping')
  saved=dict(settings._stored)
  try:
   settings._apply_value('chair_snapping','off')
   self.assertIs(settings._stored['chair_snapping'],False)
   self.assertIn('chair snapping = off',settings._render(settings._stored))
  finally:
   settings._stored.clear();settings._stored.update(saved)
 def test_busy_request_cannot_replace_the_requested_seat(self):
  self.assertTrue(self.request());saved=env.place._pending['chair_request'];serial=self.serial()
  self.assertFalse(self.request());self.assertIs(env.place._pending['chair_request'],saved)
  self.assertEqual(self.serial(),serial);self.assertTrue(self.ack())
 def test_zone_change_drops_the_request_before_creation_or_payment(self):
  self.assertTrue(self.request());env.world.zone_id=8
  self.assertFalse(self.ack());self.assertEqual(env.world.funds.money,1000);self.assertEqual(set(env.world.objects),{77})
 def test_preview_is_read_only_and_retains_native_names(self):
  parts=grid._fit_parts(self.frame);self.assertIn('Native table name',parts)
  self.assertEqual(set(env.world.objects),{77});self.assertEqual(env.world.funds.money,1000);self.assertEqual(env.place._pending['serial'],0)

if __name__=='__main__':unittest.main()
