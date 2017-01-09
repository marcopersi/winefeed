var rootURL = "http://localhost:8182/rest/cfg/apps";

findAll();

function findAll() {
	console.log('running findAll');
	$.ajax({
		type: 'GET',
		url: rootURL,
		dataType: "jsonp", // data type of response
		success: renderList,
		error: function(jqXHR, textStatus, errorThrown){
			alert('list apps error: ' + textStatus);
		}
	});
}

function renderList(data) {
	// JAX-RS serializes an empty list as null, and a 'collection of one' as an object (not an 'array of one')
	var list = data == null ? [] : (data instanceof Array ? data : [data]);

	// $('#wineList li').remove();
	$.each(list, function(index, xentisapps) {
		$('#apps').append('<li><a href="#" >'+xentisapp.identifier+'</a></li>');
	});
}

