package ch.persi.vino.gui2.client.lib;

import java.util.List;
import java.util.Map;

import com.google.gwt.user.client.rpc.RemoteService;

/**
 * The client side stub for the RPC service.
 */
public interface GenericGwtRpcService<Type> extends RemoteService {
	
    List<Type> fetch (Integer startRow, Integer endRow, String sortBy, Map<String, String> filterCriteria);

    Type add (Type data);

    Type update (Type data);

    void remove (Type data);
	
}