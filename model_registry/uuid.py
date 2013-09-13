from uuid import *

import random
import uuid
from django.db import IntegrityError
import threading
import sys
uuid_lock      =   threading.Lock()
uuid_class_lock      =   {}
uuid_class_counter   =   {}

def shall_update_uuid(uuid):
    if uuid is None or not uuid:
        return True
    elif False:#True:# TODO: Version is incompatible!
        try:
            ModelUUID(uuid=uuid).get('class_id')
            return False
        except BaseException:
            return True
    return False

def update_uuid(method, attr_prefix="", **kwargs):
    instance = kwargs.get('instance')
    sender = kwargs.get('sender')
    
    save_fields = []
    
    uuid_attr_name = "id"
    class_attr_name = attr_prefix + "class"
    
    uuid = getattr(instance, uuid_attr_name, getattr(instance, "pk", None))
    
    if shall_update_uuid(uuid):
        
        uuid = generate_uuid(sender=sender, instance=instance)
        
        setattr(instance, uuid_attr_name, uuid)
        save_fields.append(uuid_attr_name)
        
    if hasattr(instance, class_attr_name):
        
        model = sender or instance.__class__
                
        setattr(instance, class_attr_name, model._class_id)
        save_fields.append(class_attr_name)
    
    if method == 'post' and save_fields:
        try:
            instance.save(update_fields=save_fields)
        except IntegrityError:
            #try again - maybe uuid not uinique enough
            instance.save(update_fields=save_fields)

def generate_uuid(sender = None, instance=None, origin_class=None, origin=None):
    model = sender or instance.__class__
    data = {}
    
    data['class_id'] = model._class_id
    
    #_origin() #TODO # where was this creation initiated? why?
        
    #TODO settings.ACTIVE_CUSTOMER_CLUSTER
    # on staff, one can activate a customer, and than this one is being chosen
    customer_id, customer_cluster = (1, 2)
    if customer_id:
        data['customer'] = customer_id
    
    if getattr(model, "_sync", getattr(model, "_public", False)):
        data['storing_method'] = 0 # public
        
        data['origin_class'] =  origin_class or instance._uuid_get_origin_class()
        data['origin'] =        origin or instance._uuid_get_origin() #TODO # where was this creation initiated? why?
        #data['by_user'] = 0
    else:
        if False:#TODO settings.INSTANCE_TYPE  in ['hub', 'staff']
            data['storing_method'] = 1 # internal
            
            data['is_showroom'] = 0
            if False:#TODO settings.IS_SHOWROOM
                data['is_showroom'] = 1
                data['showroom'] = 0 #TODO settings.ShowroomId
                
        else:               
            try:                
                data['storing_method'] = customer_cluster
                
                data['user'] = instance.get_user_id()
            except AttributeError:
                data['storing_method'] = 0  # public
                
                data['origin_class'] =  origin_class or instance._uuid_get_origin_class()
                data['origin'] =        origin or instance._uuid_get_origin()
            
        
    if data['storing_method'] in [0, 1, 2]: # public, internal, private S
        data['is_test_data'] = 0 if True else 1 #TODO settings.IS_TEST_SYSTEM 
               
    return ModelUUID(data=data).as_string()

class ModelUUIDv0(object):
    _uuid_multicast_bit_position = 40 # 48-8
    _uuid_multicast_bit_correction_position = 1
    
    _verbose = 0
    
    _uuid__version_position = 1
    _uuid__version_length = 5
    _uuid__crypt_position = 6
    _uuid__crypt_length = 3
    _uuid__counter_position = 9
    _uuid__counter_length = 6
    
    _uuid__valid_encryptions = [1, 2] #max value: 7 (3bits)
    _uuid__encryptions = [
        lambda x, y, length: x,
        lambda x, y, length: 140737488355327 & (x ^ (int(((1 + 47/length)*bin(y | 1 << length)[3:]), 2)) ^ 93824992236885),
        lambda x, y, length: 140737488355327 & (x ^ (int(((1 + 47/length)*bin(y | 1 << length)[3:]), 2)) ^ 187649984473770),
        ]
    # 140737488355327 = int(2*'0'+47*'1', 2)
    # 93824992236885 = '01'*24
    # 187649984473770 = '10'*24
    
    @classmethod
    def encrypt(cls, node, crypt, counter):
        node = cls._uuid__encryptions[crypt](node, counter, cls._uuid__counter_length) 
        return node
    
    @classmethod
    def decrypt(cls, node, crypt, counter):
        node = cls._uuid__encryptions[crypt](node, counter, cls._uuid__counter_length) 
        return node
    
    @classmethod
    def correct_multicast(cls, node, crypt, counter):        
        value_length = len(bin(node))-2
        
        assert(
                value_length <= 47
            ), 'length 47 is "%s"' % bin(node)
        
              
        bits_before_multicast = cls._uuid_multicast_bit_position - 1
        bits_before_correction = cls._uuid_multicast_bit_correction_position - 1        
        node = node << 1
        
        
        correction  =   (
                            node >> bits_before_multicast & 1
                        ) << bits_before_correction # set first bit as correction bit
        
        node    =     (
                            node    |   correction 
                            
                        ) |  1 <<  bits_before_multicast # setting multicast bit
        
        return node
    
    @classmethod
    def undo_multicast(cls, node, crypt, counter):        
        value_length = len(bin(node))-2
        
        assert(
                value_length <= 48
            ), 'length "%s"' % bin(value_length)
        
        bits_before_multicast = cls._uuid_multicast_bit_position - 1
        bits_before_correction = cls._uuid_multicast_bit_correction_position - 1
        
        assert(
                (
                    node &
                        1 << bits_before_multicast
                ) >> bits_before_multicast
                == 1
            ), 'multicast bit "%s"' % bin(value_length) # multicast Bit should be 1 otherwise no valid uuid
        
        
        correction  =   (
                            ((node >> bits_before_correction) & 1)
                        ) << bits_before_multicast
        
        node    =     node    &   (
                                        correction | int( (48 - 1 - bits_before_multicast)* '1' + '0' + bits_before_multicast * '1', 2) #281474976710527 # 40*'1'+'0'+7*'1' ##127 # 7*'1' ###backup: 
                                    ) # setting multicast bit to multicast correction bit
        
        return node >> 1
    
    @classmethod
    def _extract_data_from_uuid(cls, orig, start_bit, length=-1):       
        
        shifted = ( orig >> start_bit-1 )
        if length == -1:
            return shifted
            
        return shifted & int( length * '1', 2)
        
        
    @classmethod
    def unpack(cls, uuid):   
        data        =   {}
        
                
        ##################
        # 14 bits = Header
        ##################
        seq         =   uuid.clock_seq 
        node        =   uuid.node                                  
                                   
        # counter - to reduce probability of duplicates
        # bits 1-6
        data['counter'] = cls._extract_data_from_uuid(
                                    seq,
                                    cls._uuid__counter_position,
                                    cls._uuid__counter_length)
        
        # used for "crypt" - so no schema can be recognized easily
        # bits 7-9        
        data['crypt'] =   cls._extract_data_from_uuid(
                                    seq,
                                    cls._uuid__crypt_position,
                                    cls._uuid__crypt_length)
        
        # Version of Model uuid
        # bits 10-14
        data['uuid_version']     =     cls._extract_data_from_uuid(
                                    seq,
                                    cls._uuid__version_position,
                                    cls._uuid__version_length)
        
        if cls._verbose > 0:
            print node
        node = cls.undo_multicast(node, data['crypt'], data['counter'])
        if cls._verbose > 0:
            print node
        node = cls.decrypt(node, data['crypt'], data['counter'])
        if cls._verbose > 0:
            print node
        
        data.update(cls.unpack_body(node))
        
        return data
    
    @classmethod
    def pack(cls, data):
        
        seq = 0
        
        # Header
        counter = data.get('counter', cls.get_random_seq_part(cls._uuid__counter_length))
        seq += cls._pack_data_in_uuid(
            counter,
            cls._uuid__counter_position,
            cls._uuid__counter_length
            )  
        
        crypt = data.get('crypt', cls.get_random_crypt_mode())
        seq += cls._pack_data_in_uuid(
            crypt,
            cls._uuid__crypt_position,
            cls._uuid__crypt_length
            )  
        
        version = cls.get_uuid_version()
        seq += cls._pack_data_in_uuid(
            version,
            cls._uuid__version_position,
            cls._uuid__version_length
            )       
        
        node = cls.pack_body(data)
        
        if cls._verbose > 0:
            print node
        node = cls.encrypt(node, crypt, counter)
        if cls._verbose > 0:
            print node
        node = cls.correct_multicast(node, crypt, counter)
        if cls._verbose > 0:
            print node
        
        _uuid = self.uuid1(
            node        =   node,
            clock_seq   =   seq
        )
        return _uuid
    
    @classmethod
    def uuid1(self, node=None, clock_seq=None):
        return uuid.uuid1(node=node, clock_seq=clock_seq)
    
    
    @classmethod
    def _pack_data_in_uuid(self, value, start_bit, length):
        assert( len(bin(value))-2 <= length ), 'length "%s"' % str(value)
        return value << (start_bit - 1) 
    
    @classmethod
    def get_random_crypt_mode(cls, ):
        return random.choice(cls._uuid__valid_encryptions)
    
    
    @classmethod
    def get_random_seq_part(cls, length):
        if True:
            # = choice(range(0,1<<length)) # max value is not in range
            return random.randrange(0,1 << length)            
        
        else:               
            # each class_id has its own counter. when accessing this counter, this access must being locked: -2-
            # by default neither this class_id specific lock nor the counter do exist. They need to be created
            # within the specific dicts. writing those dicts needs a lock on them. this lock is the global
            # uuid_lock. 
            
            global uuid_class_counter, uuid_class_lock, uuid_lock
            
            # -1-
            if not class_id in uuid_class_lock:
                # this class_id was not yet used to create a uuid in this process environment, so init it
                
                # global lock
                with uuid_lock:
                    
                    # double check, maybe some other thread did this meanwhile -possible!-
                    if not class_id in uuid_class_lock:
                        
                        # init uuid for this class_id
                        uuid_class_lock[class_id]      =   threading.Lock()
                        uuid_class_counter[class_id]   =   0
            
            
            # -2-
            # the lock for this specific class_id creation
            with uuid_class_lock[class_id]:
                
                # in the uuid is just certain space for this counter,
                # when limit is reached, reset it
                if uuid_class_counter[class_id] > 255:
                    uuid_class_counter[class_id]   =   0
                
                # store in a local var
                counter     =   uuid_class_counter[class_id]
                
                # increment thread global counter for this class
                uuid_class_counter[class_id]   +=  1
            
            
    
    
    

class ModelUUIDv1(ModelUUIDv0):
    
            
    @classmethod
    def get_uuid_version(cls, ):
        return 1

_uuid_versions = {
    ModelUUIDv1.get_uuid_version():ModelUUIDv1,
}
_uuid_latest_version = ModelUUIDv1.get_uuid_version()    

class UUIDMixin(object):
    
    @classmethod
    def _get_latest_uuid_version(cls, ):
        return _uuid_latest_version
    
    @classmethod
    def _get_uuid_class_for_version(cls, version):
        return _uuid_versions[version]
    
    @classmethod
    def _get_latest_uuid_class(cls, ):
        return cls._get_uuid_class_for_version(cls._get_latest_uuid_version())    
    
    @classmethod
    def _get_uuid_version(cls, uuid):
        # Version of Model uuid
        # bits 10-14 of clock_seq
        
        seq         =   uuid.clock_seq
        
        version = seq & 31 # int('11111', 2)
        
        return version
    @classmethod
    def _unpack_uuid(cls, uuid):
        
        version     =     cls._get_uuid_version(uuid)
        
        version_class = cls._get_uuid_class_for_version(version)
        
        return version_class.unpack(uuid)
        
    @classmethod
    def _pack_uuid(cls, data):
                    
        version = data.get('uuid_version', cls._get_latest_uuid_version())
        
        version_class = cls._get_uuid_class_for_version(version)
        
        return version_class.pack(data)



class SimpleModelUUID(UUIDMixin):
    
    def __init__(self, *args, **kwargs):
        uuid_str = kwargs.get("uuid", args[0] if len(args) > 0 else None)
        data = kwargs.get("data", args[1] if len(args) > 1 else None)
        if isinstance(uuid_str, ModelUUID):
            self._uuid      =   uuid_str.as_uuid()
        elif uuid_str is not None:
            self._uuid      =   uuid.UUID(uuid_str) if not isinstance(uuid_str, uuid.UUID) else uuid_str
        else:
            self._uuid = None
        self._data      =   data or {}            
        
    def get(self, attr):
        self._data = self._unpack_uuid(self.as_uuid())
        return self._data[attr]
        
    def as_string(self, ):
        return str(self.get_uuid())
    
    
    def as_uuid(self, ):
        return self.get_uuid()
    
    def get_uuid(self, ):
        if self._uuid:
            pass
        elif self._data:
            self._uuid = self._pack_uuid(self.get_uuid_data())
        else:
            raise Exception, 'either data or uuid needed!'
        return self._uuid
    
    def get_uuid_data(self, ):
        if self._data:
            pass
        elif self._uuid:
            self._data = self._unpack_uuid(self.as_uuid())
        else:
            raise Exception, 'either data or uuid needed!'
        return self._data
    
    def __str__(self, ):
        return str(self.get_uuid())
    
    def __unicode__(self, ):
        return unicode(self.get_uuid())
    
