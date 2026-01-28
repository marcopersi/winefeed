package ch.persi.vino.gui2.client.lib;

import java.util.List;
import java.util.Map;

import com.google.gwt.user.client.rpc.AsyncCallback;

public interface GenericGwtRpcServiceAsync<Type> {

	void add(Type data,
			AsyncCallback<Type> callback);

	void fetch(Integer startRow, Integer endRow, String sortBy, Map<String, String> filterCriteria, AsyncCallback<List<Type>> callback);

	void remove(Type data, AsyncCallback<Void> callback);

	void update(Type data,
			AsyncCallback<Type> callback);

}
