from pyteal import *

# Handle each possible OnCompletion type. We don't have to worry about
# handling ClearState, because the ClearStateProgram will execute in that
# case, not the ApprovalProgram.
def approval_program():
    # Locals
    # Globals
    on_creation = Seq(
        [
            # g int - Version
            App.globalPut(Bytes("Version"), Int(1)),
            # addr - admin
            App.globalPut(Bytes("admin"), Txn.sender()),
            # approve sequence
            Approve()
        ]
    )

    @Subroutine(TealType.bytes)
    def int_to_ascii(arg):
        """int_to_ascii converts an integer to the ascii byte that represents it"""
        return Extract(Bytes("0123456789"), arg, Int(1))

    @Subroutine(TealType.bytes)
    def itoa(i):
        """itoa converts an integer to the ascii byte string it represents"""
        return If(
            i == Int(0),
            Bytes("0"),
            Concat(
                If(i / Int(10) > Int(0), itoa(i / Int(10)), Bytes("")),
                int_to_ascii(i % Int(10)),
            ),
        )

    # Asset Trasfer
    @Subroutine(TealType.none)
    def inner_asset_transfer(asset_id: Expr, asset_amount: Expr, asset_receiver: Expr) -> Expr:
        return Seq([
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.note: Bytes("Asset Transfer"),
            TxnField.type_enum: TxnType.AssetTransfer,
            TxnField.xfer_asset: asset_id,
            TxnField.asset_amount: asset_amount,
            TxnField.asset_receiver: asset_receiver
            }),
        InnerTxnBuilder.Submit()
    ])

    # Payment
    @Subroutine(TealType.none)
    def inner_payment_txn(amount: Expr, receiver: Expr) -> Expr:
        """casual payment transaction"""
        return Seq([
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.Payment,
                TxnField.sender: Global.current_application_address(),
                TxnField.amount: amount,
                TxnField.receiver: receiver
                }),
            InnerTxnBuilder.Submit()
        ])

    # asset optIn
    @Subroutine(TealType.none)
    def optIn_assets(asset_id: Expr) -> Expr:
        return Seq(
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
		    TxnField.note: Txn.note(),
		    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.xfer_asset: asset_id,
                    TxnField.asset_receiver: Global.current_application_address(),
                    TxnField.asset_amount: Int(0),
                }
            ),
            InnerTxnBuilder.Submit(),
        )

    handle_optin = Seq([
        Approve()
    ])

    handle_closeout = Seq([
        Approve()
    ])

    # Get Admin Info
    is_admin = Txn.sender() == App.globalGet(Bytes("admin"))
    
    handle_updateapp = Seq([
        Return(is_admin)
    ])

    handle_deleteapp = Seq([
        Return(is_admin)
    ])

    optIn_assetsid = Btoi(Txn.application_args[1])
    # OptinAssetID
    optin_assetid = Seq([
        Assert(Txn.application_args.length() == Int(2)),
        optIn_assets(optIn_assetsid),
        Approve()
    ])

    version = Seq([
        Log(Concat(Bytes("Version: "), itoa(App.globalGet(Bytes("Version"))))),
        Approve()
    ])

    pay = Seq([
        Log(Bytes("Pay Txn")),
        Approve()
    ])

    #Switch cases for all noOp call's
    on_call = Cond(   
        [Txn.application_args[0] == Bytes("Version"), version],
        [Txn.type_enum() == TxnType.Payment, pay]
    )

    # Main
    program = Cond(
        [Txn.application_id() == Int(0), on_creation],
        [Txn.on_completion() == OnComplete.NoOp, on_call],
        [Txn.on_completion() == OnComplete.OptIn, handle_optin],
        [Txn.on_completion() == OnComplete.CloseOut, handle_closeout],
        [Txn.on_completion() == OnComplete.UpdateApplication, handle_updateapp],
        [Txn.on_completion() == OnComplete.DeleteApplication, handle_deleteapp]   
    )
    return program

def clear_program():
        return Return(Int(1))

if __name__ == "__main__":
    with open("approval.teal", "w") as f:
        compiled = compileTeal(approval_program(), mode=Mode.Application, version=7)
        f.write(compiled)

    with open("clear.teal", "w") as f:
        compiled = compileTeal(clear_program(), mode=Mode.Application, version=7)
        f.write(compiled)
