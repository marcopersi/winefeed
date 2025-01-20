package ch.persi.wine.feed.priceservice.controller;

import ch.persi.wine.feed.priceservice.data.PriceData;
import ch.persi.wine.feed.priceservice.repository.PriceDataRepository;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/prices")
public class PriceController {

    private final PriceDataRepository repository;

    public PriceController(PriceDataRepository repository) {
        this.repository = repository;
    }

    @GetMapping("/search")
    public List<PriceData> searchPrices(@RequestParam String keyword) {
        return repository.findByColumn1Containing(keyword);
    }
}