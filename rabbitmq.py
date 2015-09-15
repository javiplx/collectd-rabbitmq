"""
python plugin for collectd to obtain rabbitmq stats
"""
import collectd
import urllib2
import urllib
import json
import re

RABBIT_API_URL = "http://{host}:{port}/api/"

RABBITMQ_OVERVIEW = ['channels', 'connections', 'consumers', 'exchanges', 'queues']
RABBITMQ_QUEUES = ['messages', 'messages_ready', 'messages_unacknowledged']
RABBITMQ_MESSAGES = ['deliver', 'deliver_get', 'ack', 'deliver_no_ack', 'publish', 'redeliver']

RABBITMQ_VHOST = ['recv_oct', 'send_oct']

QUEUE_STATS = ['memory', 'consumers']


MESSAGE_STATS = ['publish_in', 'publish_out']

NODE_STATS = ['disk_free', 'disk_free_limit', 'fd_total',
              'fd_used', 'mem_limit', 'mem_used',
              'proc_total', 'proc_used', 'processors', 'run_queue',
              'sockets_total', 'sockets_used']
NODE_IO = [ 'io_seek_count', 'io_seek_avg_time', 'io_sync_count', 'io_sync_avg_time',
            'io_read_bytes', 'io_read_count', 'io_read_avg_time', 'io_write_bytes',
            'io_write_count', 'io_write_avg_time', 'queue_index_read_count',
            'queue_index_write_count', 'queue_index_journal_write_count',
            'mnesia_ram_tx_count', 'mnesia_disk_tx_count',
            'msg_store_read_count', 'msg_store_write_count']

PLUGIN_CONFIG = {
    'username': 'guest',
    'password': 'guest',
    'host': 'localhost',
    'port': 15672,
    'realm': 'RabbitMQ Management'
}


def configure(config_values):
    '''
    Load information from configuration file
    '''

    global PLUGIN_CONFIG
    collectd.warning('Configuring RabbitMQ Plugin')
    for config_value in config_values.children:
        collectd.warning("%s = %s" % (config_value.key,
                                   len(config_value.values) > 0))
        if len(config_value.values) > 0:
            if config_value.key == 'Username':
                PLUGIN_CONFIG['username'] = config_value.values[0]
            elif config_value.key == 'Password':
                PLUGIN_CONFIG['password'] = config_value.values[0]
            elif config_value.key == 'Host':
                PLUGIN_CONFIG['host'] = config_value.values[0]
            elif config_value.key == 'Port':
                PLUGIN_CONFIG['port'] = config_value.values[0]
            elif config_value.key == 'Realm':
                PLUGIN_CONFIG['realm'] = config_value.values[0]
            elif config_value.key == 'Ignore':
                type_rmq = config_value.values[0]
                PLUGIN_CONFIG['ignore'] = {type_rmq: []}
                for regex in config_value.children:
                    PLUGIN_CONFIG['ignore'][type_rmq].append(
                        re.compile(regex.values[0]))


def init():
    '''
    Initalize connection to rabbitmq
    '''
    collectd.warning('Initalizing RabbitMQ Plugin')


def get_info(url):
    '''
    return json object from url
    '''

    try:
        info = urllib2.urlopen(url)
    except urllib2.HTTPError as http_error:
        collectd.error("Error: %s" % (http_error))
        return None
    except urllib2.URLError as url_error:
        collectd.error("Error: %s" % (url_error))
        return None
    return json.load(info)


def dispatch_values(values, host, plugin, plugin_instance, metric_type,
                    type_instance=None):
    '''
    dispatch metrics to collectd
    Args:
      values (tuple): the values to dispatch
      host: (str): the name of the vhost
      plugin (str): the name of the plugin. Should be queue/exchange
      plugin_instance (str): the queue/exchange name
      metric_type: (str): the name of metric
      type_instance: Optional
    '''

    collectd.debug("Dispatching %s %s %s %s %s\n\t%s " % (host, plugin,
                   plugin_instance, metric_type, type_instance, values))

    metric = collectd.Values()
    if host:
        metric.host = host
    metric.plugin = plugin
    if plugin_instance:
        metric.plugin_instance = plugin_instance
    metric.type = metric_type
    if type_instance:
        metric.type_instance = type_instance
    metric.values = values
    metric.dispatch()


def want_to_ignore(type_rmq, name):
    """
    Applies ignore regex to the queue.
    """
    if 'ignore' in PLUGIN_CONFIG:
        if type_rmq in PLUGIN_CONFIG['ignore']:
            for regex in PLUGIN_CONFIG['ignore'][type_rmq]:
                match = regex.match(name)
                if match:
                    return True
    return False


def mefiltras ( values ) :
    output = []
    for v in values :
        if v is None :
            output.append( 0 )
        else :
            output.append( v )
    return output

def read(input_data=None):
    '''
    reads all metrics from rabbitmq
    '''

    collectd.debug("Reading data with input = %s" % (input_data))
    base_url = RABBIT_API_URL.format(host=PLUGIN_CONFIG['host'],
                                     port=PLUGIN_CONFIG['port'])
    collectd.warning("Asking to %s" % base_url)

    auth_handler = urllib2.HTTPBasicAuthHandler()
    auth_handler.add_password(realm=PLUGIN_CONFIG['realm'],
                              uri=base_url,
                              user=PLUGIN_CONFIG['username'],
                              passwd=PLUGIN_CONFIG['password'])
    #collectd.warning("url is = %s" % base_url)
    opener = urllib2.build_opener(auth_handler)
    urllib2.install_opener(opener)

    overview = get_info("%s/overview" % base_url)
    #collectd.warning("overview = %s" % overview)
    cluster_name = overview['cluster_name'].split('@')[1]
    values = map( overview['object_totals'].get , RABBITMQ_OVERVIEW )
    dispatch_values(values, cluster_name, 'rabbitmq', None, 'rabbit_overview')
    dispatch_values(values, cluster_name, 'rabbitmq', None, 'rabbit_overview_new')
    values = map( overview['queue_totals'].get , RABBITMQ_QUEUES )
    dispatch_values(values, cluster_name, 'rabbitmq', None, 'rabbit_queues')
    dispatch_values(values, cluster_name, 'rabbitmq', None, 'rabbit_queues_new')
    values = mefiltras( map( overview['message_stats'].get , RABBITMQ_MESSAGES ) )
    #if values[-1] is None :
    #    values[-1] = 0
    dispatch_values(values, cluster_name, 'rabbitmq', None, 'rabbit_messages')
    dispatch_values(values, cluster_name, 'rabbitmq', None, 'rabbit_messages_new')

    #First get all the nodes
    for node in get_info("%s/nodes" % (base_url)):
   #     collectd.warning("node = %s" % node)
        values = map( node.get , NODE_STATS )
   #     collectd.warning("     = %s" % values)
        collectd.warning("Dispatching %s %s\n\t%s " % ( 'rabbitmq' , 'rabbit_node' , values ) )
        if values.count(None) < 1 :
          dispatch_values(values, node['name'].split('@')[1],
                        'rabbitmq', None, 'rabbit_node')
          dispatch_values(values, node['name'].split('@')[1],
                        'rabbitmq', None, 'rabbit_node_new')
        values = mefiltras( map( node.get , NODE_IO ) )
        collectd.warning("Dispatching %s %s\n\t%s " % ( 'rabbitmq' , 'rabbit_io' , values ) )
        if values.count(None) < 1 :
          dispatch_values(values, node['name'].split('@')[1],
                        'rabbitmq', None, 'rabbit_io')
          dispatch_values(values, node['name'].split('@')[1],
                        'rabbitmq', None, 'rabbit_io_new')

    #Then get all vhost

    for vhost in get_info("%s/vhosts" % (base_url)):

        vhost_name = urllib.quote(vhost['name'], '')
        collectd.debug("Found vhost %s" % vhost['name'])
        vhost_safename = 'rabbitmq_%s' % vhost['name'].replace('/', 'default')

        collectd.warning("Asking to %s %s %s" % (base_url,vhost['name'],vhost_safename))

        if vhost.has_key( 'message_stats' ) :
            values = map( vhost.get , RABBITMQ_QUEUES + RABBITMQ_VHOST )
            dispatch_values(values, vhost_safename, 'rabbitmq', None, 'rabbit_vhost')
            collectd.warning("Dispatching %s %s\n\t%s " % ( 'rabbitmq' , 'rabbit_vhost' , values ) )
            values = mefiltras( map( vhost['message_stats'].get , RABBITMQ_MESSAGES ) )
            #if values[-1] is None :
            #    values[-1] = 0
            dispatch_values(values, vhost_safename, 'messages', None, 'rabbit_messages')
        else :
            collectd.debug("No message stats on %s (%s) at %s" % ( vhost['name'] , vhost_safename , base_url ) )

        #if vhost_name == '%2F' :
        if vhost_safename == 'rabbitmq_default' :
            collectd.warning( 'Skip queues & exchanges for default vhost' )
            continue

        #try :
        for queue in get_info("%s/queues/%s" % (base_url, vhost_name)):
            queue_name = urllib.quote(queue['name'], '')
            collectd.debug("Found queue %s" % queue['name'])
            if not want_to_ignore("queue", queue_name) and queue['durable'] :
                queue_data = get_info("%s/queues/%s/%s" % (base_url,
                                                           vhost_name,
                                                           queue_name))
                if queue_data is not None:
                    values = map( queue_data.get , RABBITMQ_QUEUES + QUEUE_STATS )
                    dispatch_values(values, vhost_safename, 'queue', queue_data['name'],
                                    'rabbit_queue') # , queue['node'].split('@')[1] )
                    #               'rabbit_queue', queue['node'].split('@')[1] )
                    dispatch_values(values, vhost_safename, 'queue', queue_data['name'],
                                    'rabbit_queue_new')
                else:
                    collectd.warning("Cannot get data back from %s/%s queue" %
                                    (vhost_name, queue_name))
        #except Exception , ex :
        #    collectd.warning("Cannot get queue data for %s %s , %s : %s" % ( base_url , vhost_name , vhost_safename , ex ) )

        #try :
        for exchange in get_info("%s/exchanges/%s" % (base_url,
                                 vhost_name)):
            exchange_name = urllib.quote(exchange['name'], '')
            if exchange_name and exchange['durable'] :
                collectd.debug("Found exchange %s" % exchange['name'])
                exchange_data = get_info("%s/exchanges/%s/%s" % (
                                         base_url, vhost_name, exchange_name))
                if exchange_data.has_key('message_stats'):
                    values = map( exchange_data['message_stats'].get , MESSAGE_STATS )
                    dispatch_values(values, vhost_safename, 'exchange', exchange_data['name'],
                                    'rabbit_exchange')
                    dispatch_values(values, vhost_safename, 'exchange', exchange_data['name'],
                                    'rabbit_exchange_new')
        #except Exception , ex :
        #    collectd.warning("Cannot get queue data for %s %s , %s : %s" % ( base_url , vhost_name , vhost_safename , ex ) )


def shutdown():
    '''
    Shutdown connection to rabbitmq
    '''

    collectd.info('RabbitMQ plugin shutting down')

# Register callbacks
collectd.register_config(configure)
collectd.register_init(init)
collectd.register_read(read)
#collectd.register_write(write)
collectd.register_shutdown(shutdown)
