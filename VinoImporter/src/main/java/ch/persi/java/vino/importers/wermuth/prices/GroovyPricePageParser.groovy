package ch.persi.java.vino.importers.wermuth.prices

import static java.lang.Integer.parseInt
import static org.apache.commons.lang3.math.NumberUtils.isNumber

Map extractByPair(groovy.util.slurpersupport.NodeChildren a) {
	SortedMap aValuesMap = new TreeMap()

	boolean start = false
	for (int i = 0; i < a.size(); i++) {
		if (a[i].toString().contains("Lot")) {
			// the next line is the start point
			start = true
		}

		if (start) {
			println("starting")
			def aLotNumber = a[i].toString().trim()
			def aPrice = a[++i].toString().trim()// change pointer increment by three, to point to the price

			print("found lotNo:" + aLotNumber)
			print("found price:" + aPrice)

			if (isNumber(aLotNumber)) {
				println("checking price: " + aPrice)
				if (isNumber(aPrice)) {
					println("storing price to map !")
					aValuesMap.put(parseInt(aLotNumber), parseInt(aPrice))
				} else {
					aValuesMap.put(parseInt(aLotNumber), null)
					println("Extracted price is not numeric, see '" + aPrice + "'")
				}

			} else {
				println("LotNumber is not numeric '" + aLotNumber + "'")
			}
		}
	}
	return aValuesMap
}

Map extractByIndex(groovy.util.slurpersupport.NodeChildren a) {
	SortedMap aValuesMap = new TreeMap()
	boolean start = false
	for (int i = 0; i < a.size(); i++) {
		if (a[i].toString().equalsIgnoreCase("Lot")) {
			// the next line is the start point
			start = true
		}

		if (start) {
			def aLotNumber = a[i].toString().trim()

			i = i + 3 // change pointer increment by three, to point to the price
			def aPrice = a[i].toString().trim()

			if (isNumber(aLotNumber)) {
				if (isNumber(aPrice)) {
					aValuesMap.put(parseInt(aLotNumber), parseInt(aPrice))
				} else {
					aValuesMap.put(parseInt(aLotNumber), null)
				}

			} else {
				print("Error, lot number must be numeric !, it is: " + aLotNumber)
			}
		}
	}
	return aValuesMap
}

Map getRealizedPrices(String theUrl) {
	def slurper = new XmlSlurper(new org.ccil.cowan.tagsoup.Parser())

	SortedMap aValuesMap = new TreeMap()

	def key = null
	def value

	html = slurper.parse(theUrl)
	def allPairs = html.body.table.tr.td

	if (html.body.table.tr[2].td.size() == 2) {
		println("running by pair - using common sense html structure")
		aValuesMap = extractByPair(html.body.table.tr.td)
	} else if (html.body.table.tbody.tr[3].td.size() == 2) {
		println("running by pair - using weird tbdoy html structure")
		aValuesMap = extractByPair(allPairs)
	} else {
		println("running by index")
		aValuesMap = extractByIndex(allPairs)
	}
	return aValuesMap
}