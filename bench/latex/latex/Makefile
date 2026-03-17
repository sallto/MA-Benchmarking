ARCH=$(shell uname -m)

.PHONY: all all-spec clean
all: parsed-bench-res figures_$(ARCH).pdf
all-spec: parsed-bench-res-spec figures_spec_$(ARCH).pdf

.PHONY: parsed-bench-res
parsed-bench-res: parsed-bench-res-$(ARCH) bench-res/parsed-umbra-$(ARCH) bench-res/parsed-test-suite-ct-$(ARCH) bench-res/parsed-test-suite-rt-text-$(ARCH)

.PHONY: parsed-bench-res-x86_64 parsed-bench-res-aarch64
parsed-bench-res-aarch64:
parsed-bench-res-x86_64: bench-res/res-wasmtime-cfa bench-res/res-wasmtime-tpde bench-res/res-wasmtime-winch bench-res/res-wasmtime-tpde-ct 

.PHONY: parsed-bench-res-spec
parsed-bench-res-spec: parsed-bench-res bench-res/parsed-spec-rt bench-res/parsed-spec-ct bench-res/parsed-spec-text

bench-res/parsed-umbra-%: bench-res/res-total-tpcdsSf1-%
	awk <$< >$@ 'BEGIN{print "backend,ct,rt"}/-[^i][^,]?,/{sub(/^.*-ct/,"TPDE-LLVM");sub(/^.*-d/,"DirectEmit");sub(/^.*-c/,"LLVM-O0");sub(/^.*-t/,"TPDE");sub(/^.*-o/,"LLVM-Opt");sub(/^.*-i/,"Interpreter");print}'

bench-res/res-wasmtime-%: bench-res/res-raw-wasmtime
	echo "bench,backend,ct,inst,rt" > bench-res/res-wasmtime-$*
	cat bench-res/res-raw-wasmtime | grep -i "$*" >> bench-res/res-wasmtime-$*
	echo -n "geomean,$*," >> bench-res/res-wasmtime-$*
	echo -n "$$(cat bench-res/res-raw-wasmtime | grep -i '$*' | awk -F',' 'BEGIN{prod=0} {prod += log($$3)} END {print exp((1/NR)*prod)}')" >> bench-res/res-wasmtime-$*
	echo -n "," >> bench-res/res-wasmtime-$*
	echo -n "$$(cat bench-res/res-raw-wasmtime | grep -i '$*' | awk -F',' 'BEGIN{prod=0} {prod += log($$4)} END {print exp((1/NR)*prod)}')" >> bench-res/res-wasmtime-$*
	echo -n "," >> bench-res/res-wasmtime-$*
	echo -n "$$(cat bench-res/res-raw-wasmtime | grep -i '$*' | awk -F',' 'BEGIN{prod=0} {prod += log($$5)} END {print exp((1/NR)*prod)}')" >> bench-res/res-wasmtime-$*

bench-res/res-wasmtime-tpde-ct: bench-res/res-raw-wasmtime-tpde-ct
	echo "translate,link,cg,analysis,prepass,sopt,misc" > bench-res/res-wasmtime-tpde-ct
	echo -n "$$(cat bench-res/res-raw-wasmtime-tpde-ct | awk -F',' 'BEGIN{sum=0} {sum += $$2} END {print (1/NR)*sum}')" >> bench-res/res-wasmtime-tpde-ct
	echo -n "," >> bench-res/res-wasmtime-tpde-ct
	echo -n "$$(cat bench-res/res-raw-wasmtime-tpde-ct | awk -F',' 'BEGIN{sum=0} {sum += $$3} END {print (1/NR)*sum}')" >> bench-res/res-wasmtime-tpde-ct
	echo -n "," >> bench-res/res-wasmtime-tpde-ct
	echo -n "$$(cat bench-res/res-raw-wasmtime-tpde-ct | awk -F',' 'BEGIN{sum=0} {sum += $$4} END {print (1/NR)*sum}')" >> bench-res/res-wasmtime-tpde-ct
	echo -n "," >> bench-res/res-wasmtime-tpde-ct
	echo -n "$$(cat bench-res/res-raw-wasmtime-tpde-ct | awk -F',' 'BEGIN{sum=0} {sum += $$5} END {print (1/NR)*sum}')" >> bench-res/res-wasmtime-tpde-ct
	echo -n "," >> bench-res/res-wasmtime-tpde-ct
	echo -n "$$(cat bench-res/res-raw-wasmtime-tpde-ct | awk -F',' 'BEGIN{sum=0} {sum += $$6} END {print (1/NR)*sum}')" >> bench-res/res-wasmtime-tpde-ct
	echo -n "," >> bench-res/res-wasmtime-tpde-ct
	echo -n "$$(cat bench-res/res-raw-wasmtime-tpde-ct | awk -F',' 'BEGIN{sum=0} {sum += $$7} END {print (1/NR)*sum}')" >> bench-res/res-wasmtime-tpde-ct
	echo -n "," >> bench-res/res-wasmtime-tpde-ct
	echo -n "$$(cat bench-res/res-raw-wasmtime-tpde-ct | awk -F',' 'BEGIN{sum=0} {sum += $$8} END {print (1/NR)*sum}')" >> bench-res/res-wasmtime-tpde-ct

SPEC_CONFIGS_RT=$(ARCH)-clang $(ARCH)-tpde o1-$(ARCH)-clang o1ir-$(ARCH)-tpde o1ir-$(ARCH)-clang 
bench-res/parsed-spec-rt: $(addprefix bench-res/res-spec-raw-rt-,$(SPEC_CONFIGS_RT))
	awk >$@ 'BEGINFILE{files[filecount++]=FILENAME;prods[FILENAME]=1;fn=FILENAME;sub(".*/","",fn);hdr=hdr","substr(fn,17)}\
		{bench[$$1]=bench[$$1]","$$2;if($$2>0){nums[FILENAME]+=1;prods[FILENAME]*=$$2}else{bench[$$1]=bench[$$1]"nan"}} \
		END{\
			print "benchmark" hdr;\
			print "600.perl" bench["600:"];\
			print "602.gcc" bench["602:"];\
			print "605.mcf" bench["605:"];\
			print "620.omnetpp" bench["620:"];\
			print "623.xalanc" bench["623:"];\
			print "625.x264" bench["625:"];\
			print "631.deepsjeng" bench["631:"];\
			print "641.leela" bench["641:"];\
			print "648.exchange2" bench["648:"];\
			print "657.xz" bench["657:"];\
			geomean="geomean";\
			for(i=0;i<filecount;i++){geomean=geomean","(prods[files[i]]**(1/nums[files[i]]))}\
			print geomean;\
		}' $^

SPEC_CONFIGS_CT=$(ARCH) o1-$(ARCH) o1ir-$(ARCH)
bench-res/res-spec-combined-ct: $(addprefix bench-res/res-spec-raw-ct-,$(SPEC_CONFIGS_CT))
	perl >$@ -ne 'use File::Basename;if(/^(6..) (.*) (.*) (.*)/){print "[\"",substr(basename($$ARGV),16),"\",$$1,\"$$3_$$2\",",eval($$4),"]\n"}' $^
bench-res/parsed-spec-ct: bench-res/res-spec-combined-ct
	jq <$< -r --slurp 'map(select(.[2]|endswith("_codegen")))|map([.[0]+"-"+(.[2]|split("_")[0]),.[1],.[3]]) as $$i |(["benchmark"]+($$i|map(.[0])|map({key:.,value:1})|from_entries|keys_unsorted)) as $$k |$$i|group_by(.[1])|map({"benchmark":.[0][1]}+(map({(.[0]):.[2]})|add)) as $$r|$$r|map(. as $$row |$$k|map($$row[.]//"nan")) as $$r | $$k, $$r[], ["geomean"]+($$r|transpose|del(.[0])|map(pow(map((if type=="number" then . else 1 end)|log2)|add|exp2;1/(map(select(type=="number"))|length)))) | @tsv' \
		| sed >$@ 's/^600/600.perl/;s/^602/602.gcc/;s/^605/605.mcf/;s/^620/620.omnetpp/;s/^623/623.xalanc/;s/^625/625.x264/;s/^631/631.deepsjeng/;s/^641/641.leela/;s/^648/648.exchange2/;s/^657/657.xz/'
bench-res/parsed-spec-text: bench-res/res-spec-combined-ct
	jq <$<  -r --slurp 'map(select(.[2]|endswith(":_text")))|map([.[0]+"-"+(.[2]|split("[_:]";null)[0]),.[1],.[3]]) as $$i |(["benchmark"]+($$i|map(.[0])|map({key:.,value:1})|from_entries|keys_unsorted)) as $$k |$$i|group_by(.[1])|map({"benchmark":.[0][1]}+(map({(.[0]):.[2]})|add)) as $$r|$$r|map(. as $$row |$$k|map($$row[.]//"nan")) as $$r |$$k, $$r[], ["geomean"]+($$r|transpose|del(.[0])|map(pow(map((if type=="number" then . else 1 end)|log2)|add|exp2;1/(map(select(type=="number"))|length)))) | @tsv' \
		| sed >$@ 's/^600/600.perl/;s/^602/602.gcc/;s/^605/605.mcf/;s/^620/620.omnetpp/;s/^623/623.xalanc/;s/^625/625.x264/;s/^631/631.deepsjeng/;s/^641/641.leela/;s/^648/648.exchange2/;s/^657/657.xz/'

bench-res/parsed-spec-ct-copypatch: bench-res/res-spec-raw-ct-x86_64 bench-res/res-spec-raw-ct-x86_64-copypatch
	echo "benchmark,value" > $@
	cat $^ | sed 's/^600/600.perl/;s/^602/602.gcc/;s/^605/605.mcf/;s/^620/620.omnetpp/;s/^623/623.xalanc/;s/^625/625.x264/;s/^631/631.deepsjeng/;s/^641/641.leela/;s/^648/648.exchange2/;s/^657/657.xz/' | grep -E "codegen clang|codegen copypatch" | sort | awk '{if (bench != $$1) { if (printed == 2) { print bench ",0" }; printed = 2; bench = $$1; val = $$4} else { printed=1; print bench "," val/$$4; lnsum += log(val/$$4); count += 1 }} END {print "geomean," exp(lnsum/count)}' >> $@

bench-res/parsed-spec-text-copypatch: bench-res/res-spec-raw-ct-x86_64 bench-res/res-spec-raw-ct-x86_64-copypatch
	echo "benchmark,value" > $@
	cat $^ | sed 's/^600/600.perl/;s/^602/602.gcc/;s/^605/605.mcf/;s/^620/620.omnetpp/;s/^623/623.xalanc/;s/^625/625.x264/;s/^631/631.deepsjeng/;s/^641/641.leela/;s/^648/648.exchange2/;s/^657/657.xz/' | grep -E "text clang|text copypatch" | sort | awk '{if (bench != $$1) { if (printed == 2) { print bench ",0" }; printed = 2; bench = $$1; val = $$4} else { printed=1; print bench "," $$4/val; lnsum += log($$4/val); count += 1 }} END {print "geomean," exp(lnsum/count)}' >> $@

bench-res/parsed-spec-rt-copypatch: bench-res/res-spec-raw-rt-x86_64-clang bench-res/res-spec-raw-rt-x86_64-copypatch
	echo "benchmark,value" > $@
	{(cat bench-res/res-spec-raw-rt-x86_64-clang | sed 's/:/ clang/'); (cat bench-res/res-spec-raw-rt-x86_64-copypatch | sed 's/:/ copypatch/'); } | sort | sed 's/^600/600.perl/;s/^602/602.gcc/;s/^605/605.mcf/;s/^620/620.omnetpp/;s/^623/623.xalanc/;s/^625/625.x264/;s/^631/631.deepsjeng/;s/^641/641.leela/;s/^648/648.exchange2/;s/^657/657.xz/' | awk '{if (bench != $$1) { if (printed == 2) { print bench ",0" }; printed = 2; bench = $$1; val = $$3} else if ($$3) { printed=1; print bench "," val/$$3; lnsum += log(val/$$3); count += 1 }} END {print "geomean," exp(lnsum/count)}' >> $@

bench-res/parsed-test-suite-ct-$(ARCH): bench-res/res-test-suite-ct-$(ARCH)
	echo "benchmark,value" > $@
	cat $^ | grep -E "codegen clang|codegen tpde" | env LC_ALL=C sort | awk '{if (bench != $$1) { if (printed == 2) { print bench ",0" }; printed = 2; bench = $$1; val = $$4} else { printed=1; print bench "," val/$$4; lnsum += log(val/$$4); count += 1 }} END {print "geomean," exp(lnsum/count)}' | sed 's/_/-/' >> $@ 

bench-res/parsed-test-suite-rt-text-$(ARCH): bench-res/res-test-suite-rt-text-$(ARCH)
	echo "benchmark,llvm-rt,tpde-rt,llvm-text,tpde-text" > $@
	cat $^ | sed 's/_/-/' >> $@

clean:
	latexmk -interaction=nonstopmode -c -pdf figures_$(ARCH).tex </dev/null
	latexmk -interaction=nonstopmode -c -pdf figures_spec_$(ARCH).tex </dev/null
	rm -f bench-res/res-wasmtime*
	-rm -f figures_$(ARCH).pdf
	-rm -f figures_spec_$(ARCH).pdf
	rm -f bench-res/parsed-*

figures_spec_x86_64.pdf:: bench-res/parsed-spec-ct-copypatch bench-res/parsed-spec-text-copypatch bench-res/parsed-spec-rt-copypatch

figures_$(ARCH).pdf:: figures_$(ARCH).tex figures_common_$(ARCH).tex parsed-bench-res
	latexmk -interaction=nonstopmode -pdf figures_$(ARCH).tex </dev/null

figures_spec_$(ARCH).pdf:: figures_spec_$(ARCH).tex figures_common_$(ARCH).tex parsed-bench-res-spec
	latexmk -interaction=nonstopmode -pdf figures_spec_$(ARCH).tex </dev/null

